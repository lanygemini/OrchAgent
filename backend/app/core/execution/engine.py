"""执行引擎：异步驱动工作流执行，协调编译器 / 流式输出 / 预算控制 / 错误处理 / checkpointer"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph

from app.core.workflow.compiler import WorkflowCompiler, DAGDefinition, DAGNode, DAGEdge, StepRecord
from app.core.workflow.state import AgentState
from app.core.execution.streamer import ExecutionStreamer
from app.core.execution.error_handler import RetryHandler, CircuitBreaker
from app.core.execution.cost_control import BudgetController, CostCalculator
from app.models.execution import WorkflowExecution, ExecutionStep
from app.models.workflow import Workflow
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """执行上下文：在执行过程中传递的元信息"""
    execution_id: str
    workflow_id: str
    workflow_name: str
    user_id: str
    input_text: str
    variables: Dict[str, Any] = field(default_factory=dict)


class ExecutionEngine:
    """工作流执行引擎 — 异步执行 DAG，支持暂停/恢复/取消，集成 LangGraph checkpointer"""

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        compiler: Optional[WorkflowCompiler] = None,
        streamer: Optional[ExecutionStreamer] = None,
        budget_controller: Optional[BudgetController] = None,
    ):
        self.db = db
        self.compiler = compiler or WorkflowCompiler()
        self.streamer = streamer or ExecutionStreamer()
        self.budget_controller = budget_controller
        self.retry_handler = RetryHandler()
        self.circuit_breaker = CircuitBreaker()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._sync_url: Optional[str] = None

    def _get_sync_url(self) -> Optional[str]:
        """获取数据库同步连接 URL（延迟加载，仅一次）"""
        if self._sync_url is None:
            try:
                from app.config import settings
                self._sync_url = settings.database_sync_url
            except Exception:
                self._sync_url = ""
        return self._sync_url or None

    async def _make_checkpointer(self):
        """创建 AsyncPostgresSaver checkpointer（每次执行创建新实例）
        AsyncPostgresSaver.from_conn_string 是 async context manager，不能缓存为单例。
        返回 async context manager 或 None。"""
        sync_url = self._get_sync_url()
        if not sync_url:
            return None

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            return AsyncPostgresSaver.from_conn_string(sync_url)
        except Exception as e:
            logger.warning("AsyncPostgresSaver 不可用，回退到 MemorySaver: %s", e)
            return None

    async def _make_memory_checkpointer(self):
        """创建 MemorySaver（内存版 checkpointer，单 worker 下 interrupt 可用，重启丢失）"""
        try:
            from langgraph.checkpoint.memory import MemorySaver
            return MemorySaver()
        except Exception:
            return None

    async def execute(
        self,
        workflow: Workflow,
        input_text: str,
        variables: Optional[Dict[str, Any]] = None,
        user_id: str = "",
        stream: bool = True,
    ) -> WorkflowExecution:
        """异步执行工作流，返回执行记录"""
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status="pending",
            input_data={"input_text": input_text, "variables": variables or {}},
            started_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)

        ctx = ExecutionContext(
            execution_id=execution.id,
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            user_id=user_id,
            input_text=input_text,
            variables=variables or {},
        )

        task = asyncio.create_task(self._run_execution(ctx, execution))
        self._active_tasks[execution.id] = task

        return execution

    async def _run_execution(self, ctx: ExecutionContext, execution: WorkflowExecution):
        """内部执行逻辑：构建 DAG → 编译 LangGraph → 执行 → 结果回写"""
        async with async_session_factory() as bg_db:
            step_records: List[StepRecord] = []

            async def record_step(step: StepRecord):
                """回调：将 StepRecord 写入 ExecutionStep 表，并推送 SSE 事件"""
                step_records.append(step)
                async with async_session_factory() as step_db:
                    exec_step = ExecutionStep(
                        execution_id=ctx.execution_id,
                        node_id=step.node_id,
                        node_label=step.node_label,
                        step_type=step.node_type,
                        input_data=step.input_data,
                        output_data=step.output_data,
                        status=step.status,
                        token_usage=step.token_usage or {},
                        error_message=step.error_message,
                        started_at=step.started_at,
                        completed_at=step.completed_at,
                    )
                    step_db.add(exec_step)
                    await step_db.commit()
                await self.streamer.publish(ctx.execution_id, "step.completed", {
                    "execution_id": ctx.execution_id,
                    "node_id": step.node_id,
                    "node_label": step.node_label,
                    "node_type": step.node_type,
                    "status": step.status,
                    "token_usage": step.token_usage or {},
                    "output_data": step.output_data or {},
                    "error_message": step.error_message,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                })

            try:
                # 预算检查前置：执行前验证用户是否在预算限额内
                if self.budget_controller and ctx.user_id:
                    budget_status = await self.budget_controller.check_budget(ctx.user_id)
                    if not budget_status.within_budget:
                        raise PermissionError(budget_status.warning or "超出预算限额，无法执行工作流")

                await bg_db.execute(
                    update(WorkflowExecution).where(WorkflowExecution.id == execution.id).values(status="running")
                )
                await bg_db.commit()

                await self.streamer.publish(ctx.execution_id, "execution.started", {
                    "execution_id": ctx.execution_id,
                    "workflow_id": ctx.workflow_id,
                    "workflow_name": ctx.workflow_name,
                })

                dag = await self._build_dag_from_workflow(bg_db, execution.workflow_id)
                await self._preload_agents(bg_db, dag)
                await self._preload_tools(bg_db, dag)
                graph = self.compiler.compile(dag, step_callback=record_step)

                initial_state: AgentState = {
                    "messages": [],
                    "workflow_id": ctx.workflow_id,
                    "execution_id": ctx.execution_id,
                    "context": {"user_input": ctx.input_text, **ctx.variables},
                    "current_node": dag.start_node_id,
                    "next_nodes": [],
                    "path": [],
                    "tool_results": {},
                    "needs_human_input": False,
                    "human_input": None,
                    "retrieved_memories": [],
                    "collected_memories": [],
                    "pending_tool_calls": None,
                    "error": None,
                }

                config = {"configurable": {"thread_id": ctx.execution_id}}

                # 尝试用 AsyncPostgresSaver（持久化 checkpointer）
                checkpointer_ctx = await self._make_checkpointer()
                if checkpointer_ctx is not None:
                    async with checkpointer_ctx as checkpointer:
                        checkpointer.setup()
                        app = graph.compile(checkpointer=checkpointer)
                        result = await app.ainvoke(initial_state, config=config)
                else:
                    # 回退到 MemorySaver（内存 checkpointer，单 worker 下 interrupt 也可用）
                    memory_checkpointer = await self._make_memory_checkpointer()
                    app = graph.compile(checkpointer=memory_checkpointer)
                    result = await app.ainvoke(initial_state, config=config)

                # 检查是否因 human 节点而中断（LangGraph interrupt 返回部分结果）
                # 此时需要将执行状态标记为 paused 而非 completed
                next_instruction = result.get("__interrupt__") if isinstance(result, dict) else None
                if next_instruction:
                    # human 节点 interrupt：执行暂停，等待人工输入
                    await bg_db.execute(
                        update(WorkflowExecution).where(WorkflowExecution.id == execution.id).values(
                            status="paused",
                        )
                    )
                    await bg_db.commit()

                    await self.streamer.publish(ctx.execution_id, "human.required", {
                        "execution_id": ctx.execution_id,
                        "message": str(next_instruction),
                    })
                    # 不发布 execution.completed，执行仍在暂停中
                    return

                total_tokens = sum(
                    (s.token_usage or {}).get("total_tokens", 0) for s in step_records
                )
                prompt_tokens = sum(
                    (s.token_usage or {}).get("prompt_tokens", 0) for s in step_records
                )
                completion_tokens = sum(
                    (s.token_usage or {}).get("completion_tokens", 0) for s in step_records
                )

                await bg_db.execute(
                    update(WorkflowExecution).where(WorkflowExecution.id == execution.id).values(
                        status="completed",
                        output_data={
                            "output": {k: str(v) for k, v in result.get("tool_results", {}).items()},
                            "path": result.get("path", []),
                        },
                        token_usage={
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens,
                        },
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await bg_db.commit()

                await self.streamer.publish(ctx.execution_id, "execution.completed", {
                    "execution_id": ctx.execution_id,
                    "status": "completed",
                })

            except Exception as e:
                logger.exception("执行引擎异常 execution_id=%s", ctx.execution_id)
                await bg_db.execute(
                    update(WorkflowExecution).where(WorkflowExecution.id == execution.id).values(
                        status="failed",
                        error_message=str(e),
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await bg_db.commit()

                await self.streamer.publish(ctx.execution_id, "execution.failed", {
                    "execution_id": ctx.execution_id,
                    "error": str(e),
                })

            finally:
                await self.streamer.publish_end(ctx.execution_id)
                self._active_tasks.pop(ctx.execution_id, None)

    async def _build_dag_from_workflow(self, db: AsyncSession, workflow_id: str) -> DAGDefinition:
        from app.models.workflow import Workflow as WF

        result = await db.execute(select(WF).where(WF.id == workflow_id))
        wf = result.scalar_one_or_none()
        if not wf:
            return DAGDefinition(nodes=[], edges=[], start_node_id="")

        nodes = [
            DAGNode(
                id=node.id,
                type=node.type,
                label=node.label,
                config=node.config or {},
                position_x=node.position_x,
                position_y=node.position_y,
                agent_id=node.agent_id,
                tool_id=node.tool_id,
            )
            for node in wf.nodes
        ]
        db_node_ids = {n.id for n in wf.nodes}

        edges = []
        for edge in wf.edges:
            edge_source = edge.source_node_id
            edge_target = edge.target_node_id
            if edge_source not in db_node_ids or edge_target not in db_node_ids:
                edge_source = next((n.id for n in wf.nodes if n.label == edge_source or getattr(n, "client_id", None) == edge_source), edge_source)
                edge_target = next((n.id for n in wf.nodes if n.label == edge_target or getattr(n, "client_id", None) == edge_target), edge_target)
            edges.append(DAGEdge(
                id=edge.id,
                source_node_id=edge_source,
                target_node_id=edge_target,
                condition_expr=edge.condition_expr,
                label=edge.label,
            ))

        start_id = wf.start_node_id or ""
        if start_id not in db_node_ids:
            start_id = next((n.id for n in wf.nodes if n.label == start_id or getattr(n, "client_id", None) == start_id), start_id)

        return DAGDefinition(nodes=nodes, edges=edges, start_node_id=start_id)

    async def _preload_agents(self, db: AsyncSession, dag: DAGDefinition):
        from app.models.agent import Agent as AgentModel

        agent_ids = {n.agent_id for n in dag.nodes if n.agent_id}
        for aid in agent_ids:
            if self.compiler.agent_manager.get_runtime(aid):
                continue
            result = await db.execute(select(AgentModel).where(AgentModel.id == aid))
            agent_model = result.scalar_one_or_none()
            if agent_model:
                self.compiler.agent_manager.create_runtime(agent_model)

    async def _preload_tools(self, db: AsyncSession, dag: DAGDefinition):
        from app.core.tool.builtin import ensure_builtin_tools
        from app.core.tool.registry import tool_registry
        from app.core.tool.base import BuiltinTool, CustomTool
        from app.models.tool import Tool as ToolModel
        from app.core.tool.builtin.calculator import CalculatorTool
        from app.core.tool.builtin.datetime_tool import DateTimeTool

        ensure_builtin_tools()

        tool_ids = {n.tool_id for n in dag.nodes if n.tool_id}
        for tid in tool_ids:
            if tool_registry.get(tid):
                continue
            result = await db.execute(select(ToolModel).where(ToolModel.id == tid))
            tool_model = result.scalar_one_or_none()
            if not tool_model:
                continue
            if tool_model.type == "builtin":
                name = tool_model.name.lower()
                if name == "calculator":
                    t = CalculatorTool()
                elif name == "datetime":
                    t = DateTimeTool()
                else:
                    from app.core.tool.base import BaseTool
                    t = BaseTool(name=tool_model.name, description=tool_model.description)
                t.tool_id = tid
                tool_registry.register(t)
            elif tool_model.type == "custom":
                t = CustomTool(
                    name=tool_model.name,
                    description=tool_model.description,
                    source_code=tool_model.config.get("source_code", ""),
                    sandbox_config=tool_model.config.get("sandbox_config", {}),
                    tool_id=tid,
                )
                tool_registry.register(t)

    async def pause(self, execution_id: str):
        """暂停执行：取消后台任务，状态由 checkpointer 保存
        human 节点的 interrupt 由 LangGraph 自动处理"""
        task = self._active_tasks.get(execution_id)
        if task:
            task.cancel()
            self._active_tasks.pop(execution_id, None)

        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = "paused"
            await self.db.flush()

    async def resume(self, execution_id: str, human_input: Optional[str] = None):
        """恢复执行：从 checkpointer 的 checkpoint 恢复，传入 human_input 继续
        LangGraph 会在 interrupt 点恢复执行"""
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return

        execution.status = "running"
        await self.db.flush()

        config = {"configurable": {"thread_id": execution_id}}

        async def _do_resume(checkpointer):
            """使用给定 checkpointer 从 interrupt 点恢复执行"""
            async with async_session_factory() as bg_db:
                dag = await self._build_dag_from_workflow(bg_db, execution.workflow_id)
                await self._preload_agents(bg_db, dag)
                await self._preload_tools(bg_db, dag)

                step_records: List[StepRecord] = []

                async def record_step(step: StepRecord):
                    step_records.append(step)
                    async with async_session_factory() as step_db:
                        exec_step = ExecutionStep(
                            execution_id=execution_id,
                            node_id=step.node_id,
                            node_label=step.node_label,
                            step_type=step.node_type,
                            input_data=step.input_data,
                            output_data=step.output_data,
                            status=step.status,
                            token_usage=step.token_usage or {},
                            error_message=step.error_message,
                            started_at=step.started_at,
                            completed_at=step.completed_at,
                        )
                        step_db.add(exec_step)
                        await step_db.commit()
                    await self.streamer.publish(execution_id, "step.completed", {
                        "execution_id": execution_id,
                        "node_id": step.node_id,
                        "node_label": step.node_label,
                        "node_type": step.node_type,
                        "status": step.status,
                    })

                graph = self.compiler.compile(dag, step_callback=record_step)
                app = graph.compile(checkpointer=checkpointer)

                # 传入 human_input 作为恢复时的状态更新
                if human_input:
                    state_update = {"human_input": human_input, "needs_human_input": False}
                    result_state = await app.ainvoke(state_update, config=config)
                else:
                    result_state = await app.ainvoke(None, config=config)

                # 检查是否再次 interrupt（多个 human 节点场景）
                next_instruction = result_state.get("__interrupt__") if isinstance(result_state, dict) else None
                if next_instruction:
                    await self.db.execute(
                        update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(
                            status="paused",
                        )
                    )
                    await self.db.commit()
                    await self.streamer.publish(execution_id, "human.required", {
                        "execution_id": execution_id,
                        "message": str(next_instruction),
                    })
                    return

                # 更新执行结果
                total_tokens = sum(
                    (s.token_usage or {}).get("total_tokens", 0) for s in step_records
                )
                await self.db.execute(
                    update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(
                        status="completed",
                        output_data={
                            "output": {k: str(v) for k, v in (result_state or {}).get("tool_results", {}).items()},
                            "path": (result_state or {}).get("path", []),
                        },
                        token_usage={"total_tokens": total_tokens},
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await self.db.commit()

                await self.streamer.publish(execution_id, "execution.completed", {
                    "execution_id": execution_id,
                    "status": "completed",
                })

        try:
            # 尝试用 AsyncPostgresSaver 恢复
            checkpointer_ctx = await self._make_checkpointer()
            if checkpointer_ctx is not None:
                async with checkpointer_ctx as checkpointer:
                    checkpointer.setup()
                    await _do_resume(checkpointer)
            else:
                # 回退到 MemorySaver（仅单 worker 环境下可用）
                memory_checkpointer = await self._make_memory_checkpointer()
                await _do_resume(memory_checkpointer)
        except Exception as e:
            logger.exception("恢复执行失败 execution_id=%s", execution_id)
            await self.db.execute(
                update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await self.db.commit()

            await self.streamer.publish(execution_id, "execution.failed", {
                "execution_id": execution_id,
                "error": str(e),
            })
        finally:
            await self.streamer.publish_end(execution_id)

    async def cancel(self, execution_id: str):
        """取消执行"""
        task = self._active_tasks.get(execution_id)
        if task:
            task.cancel()
            self._active_tasks.pop(execution_id, None)
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution:
            execution.status = "cancelled"
            execution.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
