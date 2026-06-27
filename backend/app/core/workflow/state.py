"""工作流状态定义：LangGraph StateGraph 使用的 AgentState"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


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
    workflow_id: str
    execution_id: str
    context: Dict[str, Any]                                # 上下文变量（用户输入 + 自定义变量）
    current_node: str                                      # 当前执行的节点 ID
    next_nodes: List[str]                                  # 下一批待执行节点
    path: List[str]                                        # 已执行的节点路径
    tool_results: Dict[str, Any]                           # 工具执行结果集
    needs_human_input: bool                                # 是否需要人工输入
    human_input: Optional[str]                             # 人工输入内容
    retrieved_memories: List[MemoryItem]                   # 检索到的记忆
    collected_memories: List[MemoryItem]                   # 需要存储的新记忆
    pending_tool_calls: Optional[List[Dict]]               # 待执行的工具调用
    error: Optional[str]                                   # 执行错误信息
    _last_token_usage: Optional[Dict[str, Any]]            # 上一步 Agent 调用的 token 用量
