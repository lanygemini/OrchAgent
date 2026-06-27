from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    type: str = "builtin"
    tool_schema: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    source: str = "builtin"
    source_id: Optional[str] = None


class ToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ToolResponse(BaseModel):
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
    input_data: Dict[str, Any] = {}


class ToolTestResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
