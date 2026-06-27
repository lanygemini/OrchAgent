"""工作流相关 Schema：创建 / 更新 / 响应 / 验证"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowNodeSchema(BaseModel):
    """工作流节点定义（前端 DAG 的节点）"""
    id: str
    type: str = "agent"
    label: str = ""
    config: Dict[str, Any] = {}
    position_x: float = 0.0
    position_y: float = 0.0
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None


class WorkflowEdgeSchema(BaseModel):
    """工作流边定义（前端 DAG 的连线）"""
    id: str
    source_node_id: str
    target_node_id: str
    condition_expr: Optional[str] = None
    label: str = ""


class DAGDefinition(BaseModel):
    """完整的 DAG 定义：节点 + 边 + 起始节点"""
    nodes: List[WorkflowNodeSchema]
    edges: List[WorkflowEdgeSchema]
    start_node_id: str


class WorkflowCreate(BaseModel):
    """创建工作流的请求体"""
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    dag: DAGDefinition


class WorkflowUpdate(BaseModel):
    """更新工作流的请求体（所有字段可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    dag: Optional[DAGDefinition] = None
    status: Optional[str] = None


class WorkflowResponse(BaseModel):
    """工作流响应体"""
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
    """工作流校验结果"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
