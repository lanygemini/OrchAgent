"""记忆系统 Schema：情景记忆查询 / 知识记忆 CRUD"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MemorySearchRequest(BaseModel):
    """记忆搜索请求体"""
    query: str = Field(..., min_length=1)
    top_k: int = 5


class MemoryResponse(BaseModel):
    """情景记忆响应体"""
    id: str
    agent_id: str
    session_id: Optional[str]
    content: str
    memory_type: str
    importance: float
    access_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class KnowledgeMemoryCreate(BaseModel):
    """创建知识记忆的请求体"""
    namespace: str
    key: str
    content: str
    content_type: str = "text"
    metadata: Dict[str, Any] = {}


class KnowledgeMemoryResponse(BaseModel):
    """知识记忆响应体"""
    id: str
    namespace: str
    key: str
    content: str
    content_type: str
    metadata: Dict
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
