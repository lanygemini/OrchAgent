from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    transport: str = Field(..., pattern="^(stdio|sse|streamable-http)$")
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    url: Optional[str] = None
    headers: Dict[str, str] = {}
    auth_type: str = "none"
    auth_config: Optional[Dict] = None


class MCPServerResponse(BaseModel):
    id: str
    name: str
    description: str
    transport: str
    command: Optional[str]
    args: List
    env: Dict
    url: Optional[str]
    headers: Dict
    auth_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPToolDef(BaseModel):
    name: str
    description: str
    input_schema: Dict


class MCPToolsResponse(BaseModel):
    server_id: str
    server_name: str
    tools: List[MCPToolDef]
