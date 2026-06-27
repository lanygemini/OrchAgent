"""工作流状态定义：LangGraph StateGraph 使用的 AgentState"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator


def last_write(a: Any, b: Any) -> Any:
    """最后写入者胜出（用于并行分支的非合并字段）"""
    return b


def merge_tool_results(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """合并并行分支的 tool_results"""
    r = dict(a)
    r.update(b)
    return r


class MemoryItem(TypedDict):
    """记忆条目类型"""
    id: str
    content: str
    memory_type: str
    importance: float
    created_at: str


class AgentState(TypedDict, total=False):
    """工作流执行状态 — 在工作流各节点间流转的数据载体"""
    messages: Annotated[List[BaseMessage], add_messages]  # 对话消息历史（LangGraph 自动合并）
    workflow_id: Annotated[str, last_write]
    execution_id: Annotated[str, last_write]
    context: Dict[str, Any]
    current_node: Annotated[str, last_write]
    next_nodes: List[str]
    path: Annotated[List[str], operator.add]               # 已执行的节点路径（增量合并）
    tool_results: Annotated[Dict[str, Any], merge_tool_results]  # 工具执行结果集（并行安全）
    needs_human_input: Annotated[bool, last_write]
    human_input: Optional[str]
    retrieved_memories: List[MemoryItem]
    collected_memories: List[MemoryItem]
    pending_tool_calls: Optional[List[Dict]]
    error: Annotated[Optional[str], last_write]
    _last_token_usage: Annotated[Optional[Dict[str, Any]], last_write]
