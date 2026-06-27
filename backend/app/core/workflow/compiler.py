from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.workflow.state import AgentState
from app.core.agent.agent_manager import AgentManager, AgentRuntime
from app.core.tool.registry import tool_registry
from app.core.memory.episodic import EpisodicMemoryStore
from app.core.memory.extractor import MemoryExtractor


@dataclass
class DAGNode:
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
    id: str
    source_node_id: str
    target_node_id: str
    condition_expr: Optional[str] = None
    label: str = ""


@dataclass
class DAGDefinition:
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    start_node_id: str


class ValidationError(Exception):
    pass


class WorkflowCompiler:
    def __init__(
        self,
        agent_manager: Optional[AgentManager] = None,
        memory_store: Optional[EpisodicMemoryStore] = None,
    ):
        self.agent_manager = agent_manager or AgentManager()
        self.memory_store = memory_store

    def validate(self, dag: DAGDefinition) -> List[str]:
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

    def compile(self, dag: DAGDefinition) -> StateGraph:
        errors = self.validate(dag)
        if errors:
            raise ValidationError("；".join(errors))

        graph = StateGraph(AgentState)

        graph.set_entry_point(dag.start_node_id)

        for node in dag.nodes:
            handler = self._get_node_handler(node)
            graph.add_node(node.id, handler)

        edges_from_source: Dict[str, List[DAGEdge]] = {}
        for edge in dag.edges:
            edges_from_source.setdefault(edge.source_node_id, []).append(edge)

        for node in dag.nodes:
            outgoing = edges_from_source.get(node.id, [])
            if len(outgoing) == 1:
                edge = outgoing[0]
                if edge.condition_expr:
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
                has_conditions = any(e.condition_expr for e in outgoing)
                if has_conditions:
                    def make_router(edges: List[DAGEdge]):
                        def router(state: AgentState) -> str:
                            for edge in edges:
                                if edge.condition_expr:
                                    try:
                                        result = eval(edge.condition_expr, {"state": state, "context": state.get("context", {})})
                                        if result:
                                            return edge.target_node_id
                                    except Exception:
                                        continue
                            return edges[-1].target_node_id
                        return router
                    branch_map = {e.target_node_id: e.target_node_id for e in outgoing}
                    graph.add_conditional_edges(node.id, make_router(outgoing), branch_map)
                else:
                    for edge in outgoing:
                        graph.add_edge(node.id, edge.target_node_id)

        return graph

    def _get_node_handler(self, node: DAGNode) -> Callable:
        handlers = {
            "agent": self._handle_agent_node,
            "tool": self._handle_tool_node,
            "condition": self._handle_condition_node,
            "start": self._handle_start_node,
            "end": self._handle_end_node,
            "fork": self._handle_fork_node,
            "join": self._handle_join_node,
            "human": self._handle_human_node,
        }
        return handlers.get(node.type, self._handle_noop)

    async def _handle_start_node(self, state: AgentState) -> AgentState:
        return state

    async def _handle_end_node(self, state: AgentState) -> AgentState:
        return state

    async def _handle_noop(self, state: AgentState) -> AgentState:
        return state

    async def _handle_agent_node(self, state: AgentState) -> AgentState:
        agent_id = state.get("current_node", "")
        runtime = self.agent_manager.get_runtime(agent_id)
        if not runtime:
            state["error"] = f"Agent runtime not found for node: {agent_id}"
            return state

        user_input = state["messages"][-1].content if state["messages"] else ""
        response = runtime.invoke(user_input)
        state["tool_results"][agent_id] = response.content
        return state

    async def _handle_tool_node(self, state: AgentState) -> AgentState:
        tool_id = state.get("current_node", "")
        tool = tool_registry.get(tool_id)
        if not tool:
            state["error"] = f"Tool not found: {tool_id}"
            return state
        result = await tool._arun(**state.get("context", {}))
        state["tool_results"][tool_id] = result
        return state

    async def _handle_condition_node(self, state: AgentState) -> AgentState:
        return state

    async def _handle_fork_node(self, state: AgentState) -> AgentState:
        return state

    async def _handle_join_node(self, state: AgentState) -> AgentState:
        return state

    async def _handle_human_node(self, state: AgentState) -> AgentState:
        state["needs_human_input"] = True
        return state
