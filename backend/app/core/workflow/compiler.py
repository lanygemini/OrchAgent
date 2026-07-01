"""工作流编译器：将 DAG 定义编译为可执行的 LangGraph StateGraph"""
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.workflow.state import AgentState
from app.core.agent.agent_manager import AgentManager, AgentRuntime
from app.core.tool.registry import tool_registry
from app.core.memory.episodic import EpisodicMemoryStore
from app.core.memory.extractor import MemoryExtractor


@dataclass
class StepRecord:
    """节点执行步骤记录"""
    node_id: str
    node_label: str
    node_type: str
    status: str = "running"
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


StepCallback = Callable[[StepRecord], Awaitable[None]]


@dataclass
class DAGNode:
    """DAG 节点定义"""
    id: str
    type: str
    label: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None


@dataclass
class DAGEdge:
    """DAG 边定义"""
    id: str
    source_node_id: str
    target_node_id: str
    condition_expr: Optional[str] = None
    label: str = ""


@dataclass
class DAGDefinition:
    """完整的 DAG 定义"""
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    start_node_id: str


class ValidationError(Exception):
    """工作流校验失败异常"""
    pass


class WorkflowCompiler:
    """将 DAG 定义编译为 LangGraph StateGraph，每种节点类型对应一个 handler"""

    def __init__(
        self,
        agent_manager: Optional[AgentManager] = None,
        memory_store: Optional[EpisodicMemoryStore] = None,
    ):
        self.agent_manager = agent_manager or AgentManager()
        self.memory_store = memory_store

    def validate(self, dag: DAGDefinition) -> List[str]:
        """校验 DAG 定义：检查节点完整性、边的合法性"""
        errors = []
        node_ids = {n.id for n in dag.nodes}

        if not dag.start_node_id:
            errors.append("工作流必须有一个起始节点")
        elif dag.start_node_id not in node_ids:
            errors.append(f"起始节点 '{dag.start_node_id}' 在节点列表中不存在")

        for edge in dag.edges:
            if edge.source_node_id not in node_ids:
                errors.append(f"边的源节点 '{edge.source_node_id}' 不存在")
            if edge.target_node_id not in node_ids:
                errors.append(f"边的目标节点 '{edge.target_node_id}' 不存在")

        return errors

    def compile(self, dag: DAGDefinition, step_callback: Optional[StepCallback] = None) -> StateGraph:
        """将 DAG 编译为 LangGraph StateGraph，step_callback 在每个节点执行后触发
        human 节点自动设置 interrupt_before，使图执行到此暂停等待人工输入"""
        errors = self.validate(dag)
        if errors:
            raise ValidationError("；".join(errors))

        graph = StateGraph(AgentState)

        graph.set_entry_point(dag.start_node_id)

        node_map: Dict[str, DAGNode] = {n.id: n for n in dag.nodes}
        # 收集 human 节点 ID，用于设置 interrupt_before
        human_node_ids: List[str] = []

        for node in dag.nodes:
            handler = self._get_node_handler(node, step_callback)
            graph.add_node(node.id, handler)
            if node.type == "human":
                human_node_ids.append(node.id)

        # 按源节点分组边
        edges_from_source: Dict[str, List[DAGEdge]] = {}
        for edge in dag.edges:
            edges_from_source.setdefault(edge.source_node_id, []).append(edge)

        for node in dag.nodes:
            outgoing = edges_from_source.get(node.id, [])
            if len(outgoing) == 1:
                edge = outgoing[0]
                if edge.condition_expr:
                    # 单条条件边（条件评估为真时走此边）
                    def make_router(expr: str):
                        def router(state: AgentState) -> str:
                            try:
                                result = eval(expr, {"state": state, "context": state.get("context", {})})
                                return str(result).lower()
                            except Exception:
                                return edge.target_node_id
                        return router
                    graph.add_conditional_edges(node.id, make_router(edge.condition_expr), {edge.target_node_id: edge.target_node_id})
                else:
                    graph.add_edge(node.id, edge.target_node_id)
            elif len(outgoing) > 1:
                # 多条出边
                source_node = node_map.get(node.id)
                is_fork = source_node and source_node.type == "fork"
                has_conditions = any(e.condition_expr for e in outgoing)

                if is_fork and not has_conditions:
                    # fork 节点：多条无条件出边 → LangGraph 自动并行执行
                    for edge in outgoing:
                        graph.add_edge(node.id, edge.target_node_id)
                elif has_conditions:
                    # 条件分支路由
                    def make_router(edges: List[DAGEdge]):
                        def router(state: AgentState) -> List[str]:
                            """条件路由：返回目标节点 ID 列表（支持多目标并行）"""
                            targets = []
                            for edge in edges:
                                if edge.condition_expr:
                                    try:
                                        result = eval(edge.condition_expr, {"state": state, "context": state.get("context", {})})
                                        if result:
                                            targets.append(edge.target_node_id)
                                    except Exception:
                                        continue
                            # 无条件匹配时走最后一条边（默认分支）
                            if not targets:
                                targets.append(edges[-1].target_node_id)
                            return targets if len(targets) > 1 else targets[0]
                        return router
                    branch_map = {e.target_node_id: e.target_node_id for e in outgoing}
                    graph.add_conditional_edges(node.id, make_router(outgoing), branch_map)
                else:
                    # 非 fork 的多条无条件出边（也按并行处理）
                    for edge in outgoing:
                        graph.add_edge(node.id, edge.target_node_id)

        # 设置 human 节点在执行前中断，等待人工输入
        if human_node_ids:
            graph.interrupt_before = human_node_ids

        return graph

    def _get_node_handler(self, node: DAGNode, step_callback: Optional[StepCallback] = None) -> Callable:
        """根据节点类型返回对应的处理函数（闭包绑定节点配置），并用 step_callback 记录步骤"""
        async def handler(state: AgentState) -> AgentState:
            step = StepRecord(
                node_id=node.id,
                node_label=node.label or node.type,
                node_type=node.type,
                status="running",
                input_data=dict(state.get("context", {})),
                started_at=datetime.now(timezone.utc),
            )

            changes: Dict[str, Any] = {"current_node": node.id, "path": [node.id]}

            try:
                if node.type == "agent":
                    await self._handle_agent_node(state, changes, node.agent_id)
                elif node.type == "tool":
                    await self._handle_tool_node(state, changes, node.tool_id, node.config)
                elif node.type == "condition":
                    await self._handle_condition_node(state, changes)
                elif node.type == "start":
                    await self._handle_start_node(state, changes)
                elif node.type == "end":
                    await self._handle_end_node(state, changes)
                elif node.type == "fork":
                    await self._handle_fork_node(state, changes)
                elif node.type == "join":
                    await self._handle_join_node(state, changes)
                elif node.type == "human":
                    await self._handle_human_node(state, changes)
                else:
                    await self._handle_noop(state, changes)

                state_err = state.get("error") or changes.get("error")
                if state_err:
                    step.status = "failed"
                    step.error_message = state_err
                else:
                    step.status = "completed"

                # merge changes back to state for step recording
                state.update(changes)
                step.output_data = {
                    "tool_results": {k: str(v)[:500] for k, v in state.get("tool_results", {}).items()},
                }
                if node.type == "agent":
                    step.token_usage = dict(changes.get("_last_token_usage") or {})
            except Exception as e:
                step.status = "failed"
                step.error_message = str(e)
                changes["error"] = str(e)

            step.completed_at = datetime.now(timezone.utc)

            if step_callback:
                await step_callback(step)

            return changes
        return handler

    async def _handle_start_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """起始节点：透传状态"""
        pass

    async def _handle_end_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """结束节点：透传状态"""
        pass

    async def _handle_noop(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """空操作节点"""
        pass

    async def _handle_agent_node(self, state: AgentState, changes: Dict[str, Any], agent_id: Optional[str]) -> None:
        """Agent 节点：调用 AgentRuntime 进行处理"""
        if not agent_id:
            changes["error"] = "Agent 节点未配置 agent_id"
            return
        runtime = self.agent_manager.get_runtime(agent_id)
        if not runtime:
            changes["error"] = f"Agent 运行时未找到，agent_id: {agent_id}"
            return

        user_input = state.get("context", {}).get("user_input", "")
        if state.get("messages"):
            user_input = state["messages"][-1].content if hasattr(state["messages"][-1], 'content') else str(state["messages"][-1])
        try:
            response = runtime.invoke(user_input)
            from langchain_core.messages import AIMessage
            changes["messages"] = [AIMessage(content=response.content)]
            changes["tool_results"] = {agent_id: response.content}
            changes["_last_token_usage"] = response.token_usage
        except Exception as e:
            changes["error"] = f"Agent 调用失败: {str(e)}"

    async def _handle_tool_node(self, state: AgentState, changes: Dict[str, Any], tool_id: Optional[str], config: Dict[str, Any]) -> None:
        """工具节点：调用注册的工具执行，config 中的参数优先于 context"""
        if not tool_id:
            changes["error"] = "工具节点未配置 tool_id"
            return
        tool = tool_registry.get(tool_id)
        if not tool:
            changes["error"] = f"工具未找到: {tool_id}"
            return
        try:
            kwargs = dict(config) if config else {}
            result = await tool._arun(**kwargs)
            changes["tool_results"] = {tool_id: result}
        except Exception as e:
            changes["error"] = f"工具调用失败: {str(e)}"

    async def _handle_condition_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """条件节点：求值条件表达式，将结果写入 context 供边上路由使用"""
        # 条件节点的实际路由由边上的条件表达式完成
        # 此处仅标记当前节点已执行，供日志追踪
        changes["context"] = {**state.get("context", {}), "_condition_evaluated": True}

    async def _handle_fork_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """分支节点：标记并行分支开始，将当前上下文快照传递给各分支
        LangGraph 通过多条出边自动并行执行，此节点负责保存分支前的状态快照"""
        # 保存分支前的 tool_results 快照，供 join 节点合并时使用
        existing_results = dict(state.get("tool_results", {}))
        changes["context"] = {
            **state.get("context", {}),
            "_fork_snapshot": existing_results,
        }

    async def _handle_join_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """汇合节点：聚合并行分支结果
        merge_tool_results reducer 已自动合并各分支的 tool_results，
        此处汇总 token 用量并清理分支快照"""
        current_results = state.get("tool_results", {})
        context = dict(state.get("context", {}))

        # 汇总各分支的 token 用量
        total_prompt = 0
        total_completion = 0
        total_total = 0
        for key, value in current_results.items():
            if isinstance(value, dict) and "token_usage" in value:
                tu = value["token_usage"]
                total_prompt += tu.get("prompt_tokens", 0)
                total_completion += tu.get("completion_tokens", 0)
                total_total += tu.get("total_tokens", 0)

        if total_total > 0:
            changes["_last_token_usage"] = {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_total,
            }

        # 清理分支快照
        context.pop("_fork_snapshot", None)
        changes["context"] = context

    async def _handle_human_node(self, state: AgentState, changes: Dict[str, Any]) -> None:
        """人工节点：标记需要人工输入，配合 LangGraph interrupt 实现真正暂停
        需在 compile 时对 human 节点设置 interrupt_before，使图执行到此暂停"""
        changes["needs_human_input"] = True
        # 如果已有 human_input（resume 后传入），则清除暂停标记继续执行
        if state.get("human_input"):
            changes["needs_human_input"] = False
