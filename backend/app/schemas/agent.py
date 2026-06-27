from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
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
    items: List[AgentResponse]
    total: int
    page: int
    page_size: int


class AgentTestRequest(BaseModel):
    input_text: str
    stream: bool = True
