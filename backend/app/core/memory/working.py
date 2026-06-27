"""记忆模块状态引用 — 统一从 workflow/state 导入，避免重复定义"""
from app.core.workflow.state import AgentState, MemoryItem

__all__ = ["AgentState", "MemoryItem"]
