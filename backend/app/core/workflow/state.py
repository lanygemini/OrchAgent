from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class MemoryItem(TypedDict):
    id: str
    content: str
    memory_type: str
    importance: float
    created_at: str


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    workflow_id: str
    execution_id: str
    context: Dict[str, Any]
    current_node: str
    next_nodes: List[str]
    path: List[str]
    tool_results: Dict[str, Any]
    needs_human_input: bool
    human_input: Optional[str]
    retrieved_memories: List[MemoryItem]
    collected_memories: List[MemoryItem]
    pending_tool_calls: Optional[List[Dict]]
    error: Optional[str]
