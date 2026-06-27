from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from app.dependencies import get_db, get_current_user
from app.models.execution import WorkflowExecution, ExecutionStep
from app.models.workflow import Workflow
from app.schemas.execution import ExecuteRequest, ExecutionResponse, ExecutionStepResponse

router = APIRouter(prefix="/api/v1/executions", tags=["执行管理"])


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse, status_code=202)
async def execute_workflow(
    workflow_id: str,
    data: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    wf_result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = wf_result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")

    execution = WorkflowExecution(
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        status="pending",
        input_data={"input_text": data.input_text, "variables": data.variables},
        created_by=user.sub,
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    return ExecutionResponse(
        id=execution.id,
        workflow_id=execution.workflow_id,
        workflow_name=execution.workflow_name,
        status=execution.status,
        input_data=execution.input_data or {},
        step_count=0,
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    steps_result = await db.execute(
        select(ExecutionStep).where(ExecutionStep.execution_id == execution_id)
    )
    steps = steps_result.scalars().all()

    return ExecutionResponse(
        id=execution.id,
        workflow_id=execution.workflow_id,
        workflow_name=execution.workflow_name,
        status=execution.status,
        input_data=execution.input_data or {},
        output_data=execution.output_data,
        token_usage=execution.token_usage or {},
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        error_message=execution.error_message,
        step_count=len(steps),
    )


@router.get("/{execution_id}/stream")
async def stream_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {"message": "SSE 流式输出端点（实现待完成）", "execution_id": execution_id}


@router.get("/{execution_id}/steps")
async def list_execution_steps(execution_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExecutionStep).where(ExecutionStep.execution_id == execution_id).order_by(ExecutionStep.started_at)
    )
    steps = result.scalars().all()
    return {"items": [ExecutionStepResponse.model_validate(s) for s in steps]}


@router.post("/{execution_id}/pause", status_code=200)
async def pause_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return {"message": "暂停端点（实现待完成）", "execution_id": execution_id}


@router.post("/{execution_id}/resume", status_code=200)
async def resume_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return {"message": "恢复端点（实现待完成）", "execution_id": execution_id}


@router.post("/{execution_id}/cancel", status_code=200)
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return {"message": "取消端点（实现待完成）", "execution_id": execution_id}
