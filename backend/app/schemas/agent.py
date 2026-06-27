"""Agent 相关 Pydantic Schema：请求 / 响应数据模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """创建 Agent 的请求体"""
    name: str = Field(..., min_length=1, max_length=128)
    role: str = "助手"
    description: str = ""
    llm_provider: str = Field(..., pattern="^(openai|deepseek|qwen|zhipu)$")
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    enable_memory: bool = True
    memory_window: int = 10
    memory_policy: str = "private"


class AgentUpdate(BaseModel):
    """更新 Agent 的请求体（所有字段可选）"""
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    enable_memory: Optional[bool] = None
    memory_window: Optional[int] = None
    memory_policy: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent 响应体"""
    id: str
    name: str
    role: str
    description: str
    llm_provider: str
    model_name: str
    temperature: float
    max_tokens: int
    system_prompt: str
    enable_memory: bool
    memory_window: int
    memory_policy: str
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Agent 列表响应体（带分页）"""
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int


class AgentTestRequest(BaseModel):
    """测试 Agent 的请求体"""
    input_text: str
    stream: bool = True
