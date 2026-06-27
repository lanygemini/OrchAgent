"""工具相关 Schema：注册、更新、测试"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    """注册工具的请求体"""
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    type: str = "builtin"
    tool_schema: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    source: str = "builtin"
    source_id: Optional[str] = None


class ToolUpdate(BaseModel):
    """更新工具的请求体"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ToolResponse(BaseModel):
    """工具响应体"""
    id: str
    name: str
    description: str
    type: str
    tool_schema: Dict
    config: Dict
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolTestRequest(BaseModel):
    """测试工具的请求体"""
    input_data: Dict[str, Any] = {}


class ToolTestResponse(BaseModel):
    """测试工具的响应体"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
