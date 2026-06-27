from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowNodeSchema(BaseModel):
    id: str
    type: str = "agent"
    label: str = ""
    config: Dict[str, Any] = {}
    position_x: float = 0.0
    position_y: float = 0.0
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None


class WorkflowEdgeSchema(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    condition_expr: Optional[str] = None
    label: str = ""


class DAGDefinition(BaseModel):
    nodes: List[WorkflowNodeSchema]
    edges: List[WorkflowEdgeSchema]
    start_node_id: str


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    dag: DAGDefinition


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dag: Optional[DAGDefinition] = None
    status: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    dag: Optional[Dict] = None
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
