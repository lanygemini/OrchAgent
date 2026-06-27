import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph

from app.core.workflow.compiler import WorkflowCompiler, DAGDefinition, DAGNode, DAGEdge
from app.core.workflow.state import AgentState
from app.core.execution.streamer import ExecutionStreamer
from app.core.execution.error_handler import RetryHandler, CircuitBreaker
from app.core.execution.cost_control import BudgetController, CostCalculator
from app.models.execution import WorkflowExecution, ExecutionStep
from app.models.workflow import Workflow


@dataclass
class ExecutionContext:
    execution_id: str
    workflow_id: str
    workflow_name: str
    user_id: str
    input_text: str
    variables: Dict[str, Any] = field(default_factory=dict)


class ExecutionEngine:
    def __init__(
        self,
        db: AsyncSession,
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

    async def execute(
        self,
        workflow: Workflow,
        input_text: str,
        variables: Optional[Dict[str, Any]] = None,
        user_id: str = "",
        stream: bool = True,
    ) -> WorkflowExecution:
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
        try:
            execution.status = "running"
            await self.db.flush()

            await self.streamer.publish(ctx.execution_id, "execution.started", {
                "execution_id": ctx.execution_id,
                "workflow_id": ctx.workflow_id,
                "workflow_name": ctx.workflow_name,
            })

            dag = self._build_dag_from_workflow(execution.workflow_id)
            graph = self.compiler.compile(dag)

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

            app = graph.compile()
            result = await app.ainvoke(initial_state)

            execution.status = "completed"
            execution.output_data = {"output": str(result.get("tool_results", {})), "path": result.get("path", [])}
            execution.completed_at = datetime.now(timezone.utc)

            await self.streamer.publish(ctx.execution_id, "execution.completed", {
                "execution_id": ctx.execution_id,
                "status": "completed",
            })

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)

            await self.streamer.publish(ctx.execution_id, "execution.failed", {
                "execution_id": ctx.execution_id,
                "error": str(e),
            })

        finally:
            await self.db.flush()
            self._active_tasks.pop(ctx.execution_id, None)

    def _build_dag_from_workflow(self, workflow_id: str) -> DAGDefinition:
        return DAGDefinition(nodes=[], edges=[], start_node_id="")

    async def pause(self, execution_id: str):
        task = self._active_tasks.get(execution_id)
        if task:
            task.cancel()
            self._active_tasks.pop(execution_id, None)
        async with self.db.begin():
            result = await self.db.execute(
                __import__("sqlalchemy").select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = "paused"
                await self.db.flush()

    async def resume(self, execution_id: str, human_input: Optional[str] = None):
        async with self.db.begin():
            result = await self.db.execute(
                __import__("sqlalchemy").select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = "running"
                await self.db.flush()

    async def cancel(self, execution_id: str):
        task = self._active_tasks.get(execution_id)
        if task:
            task.cancel()
            self._active_tasks.pop(execution_id, None)
        async with self.db.begin():
            result = await self.db.execute(
                __import__("sqlalchemy").select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            if execution:
                execution.status = "cancelled"
                execution.completed_at = datetime.now(timezone.utc)
                await self.db.flush()
