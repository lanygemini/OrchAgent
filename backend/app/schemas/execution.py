from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    input_text: str
    variables: Dict[str, Any] = {}
    stream: bool = True


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: str
    input_data: Dict
    output_data: Optional[Dict] = None
    token_usage: TokenUsage = TokenUsage()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    step_count: int = 0

    model_config = {"from_attributes": True}


class ExecutionStepResponse(BaseModel):
    id: str
    execution_id: str
    node_id: str
    node_label: str
    step_type: str
    input_data: Optional[Dict] = None
    output_data: Optional[Dict] = None
    status: str
    error_message: Optional[str] = None
    token_usage: TokenUsage = TokenUsage()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
