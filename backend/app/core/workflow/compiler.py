"""工作流编译器：将 DAG 定义编译为可执行的 LangGraph StateGraph"""
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

    def compile(self, dag: DAGDefinition) -> StateGraph:
        """将 DAG 编译为 LangGraph StateGraph"""
        errors = self.validate(dag)
        if errors:
            raise ValidationError("；".join(errors))

        graph = StateGraph(AgentState)

        graph.set_entry_point(dag.start_node_id)

        for node in dag.nodes:
            handler = self._get_node_handler(node)
            graph.add_node(node.id, handler)

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
                # 多条出边：条件分支路由
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
        """根据节点类型返回对应的处理函数（闭包绑定节点配置）"""
        async def handler(state: AgentState) -> AgentState:
            state["current_node"] = node.id

            if node.type == "agent":
                return await self._handle_agent_node(state, node.agent_id)
            elif node.type == "tool":
                return await self._handle_tool_node(state, node.tool_id)
            elif node.type == "condition":
                return await self._handle_condition_node(state)
            elif node.type == "start":
                return await self._handle_start_node(state)
            elif node.type == "end":
                return await self._handle_end_node(state)
            elif node.type == "fork":
                return await self._handle_fork_node(state)
            elif node.type == "join":
                return await self._handle_join_node(state)
            elif node.type == "human":
                return await self._handle_human_node(state)
            else:
                return await self._handle_noop(state)
        return handler

    async def _handle_start_node(self, state: AgentState) -> AgentState:
        """起始节点：透传状态"""
        state["path"] = state.get("path", []) + [state.get("current_node", "start")]
        return state

    async def _handle_end_node(self, state: AgentState) -> AgentState:
        """结束节点：透传状态"""
        state["path"] = state.get("path", []) + [state.get("current_node", "end")]
        return state

    async def _handle_noop(self, state: AgentState) -> AgentState:
        """空操作节点"""
        state["path"] = state.get("path", []) + [state.get("current_node", "noop")]
        return state

    async def _handle_agent_node(self, state: AgentState, agent_id: Optional[str]) -> AgentState:
        """Agent 节点：调用 AgentRuntime 进行处理"""
        state["path"] = state.get("path", []) + [state.get("current_node", "agent")]
        if not agent_id:
            state["error"] = "Agent 节点未配置 agent_id"
            return state
        runtime = self.agent_manager.get_runtime(agent_id)
        if not runtime:
            state["error"] = f"Agent 运行时未找到，node_id: {state.get('current_node', '')}, agent_id: {agent_id}"
            return state

        user_input = state["context"].get("user_input", "")
        if state["messages"]:
            user_input = state["messages"][-1].content if hasattr(state["messages"][-1], 'content') else str(state["messages"][-1])
        try:
            response = runtime.invoke(user_input)
            state["tool_results"][agent_id] = response.content
        except Exception as e:
            state["error"] = f"Agent 调用失败: {str(e)}"
        return state

    async def _handle_tool_node(self, state: AgentState, tool_id: Optional[str]) -> AgentState:
        """工具节点：调用注册的工具执行"""
        if not tool_id:
            state["error"] = "工具节点未配置 tool_id"
            return state
        tool = tool_registry.get(tool_id)
        if not tool:
            state["error"] = f"工具未找到: {tool_id}"
            return state
        try:
            result = await tool._arun(**state.get("context", {}))
            state["tool_results"][tool_id] = result
        except Exception as e:
            state["error"] = f"工具调用失败: {str(e)}"
        return state

    async def _handle_condition_node(self, state: AgentState) -> AgentState:
        """条件节点：占位，由边上的条件表达式处理"""
        return state

    async def _handle_fork_node(self, state: AgentState) -> AgentState:
        """分支节点：占位"""
        return state

    async def _handle_join_node(self, state: AgentState) -> AgentState:
        """汇合节点：占位"""
        return state

    async def _handle_human_node(self, state: AgentState) -> AgentState:
        """人工节点：标记需要人工输入"""
        state["needs_human_input"] = True
        return state
