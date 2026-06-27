"""执行管理 API：触发执行、查询状态、SSE 流式输出、暂停/恢复/取消"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.models.execution import WorkflowExecution, ExecutionStep
from app.models.workflow import Workflow
from app.schemas.execution import ExecuteRequest, ExecutionResponse, ExecutionStepResponse
from app.core.execution.engine import ExecutionEngine
from app.core.execution.streamer import ExecutionStreamer

router = APIRouter(prefix="/api/v1/executions", tags=["执行管理"])

_engine: Optional[ExecutionEngine] = None
_streamer: Optional[ExecutionStreamer] = None


def _get_engine() -> ExecutionEngine:
    global _engine
    if _engine is None:
        _engine = ExecutionEngine(db=None)
    return _engine


def _get_streamer() -> ExecutionStreamer:
    global _streamer
    if _streamer is None:
        _streamer = ExecutionStreamer()
    return _streamer


@router.get("")
async def list_executions(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取执行记录列表"""
    conditions = [WorkflowExecution.created_by == user.sub]
    if workflow_id:
        conditions.append(WorkflowExecution.workflow_id == workflow_id)
    if status:
        conditions.append(WorkflowExecution.status == status)

    result = await db.execute(
        select(WorkflowExecution).where(*conditions).order_by(WorkflowExecution.created_at.desc()).offset(offset).limit(limit)
    )
    executions = result.scalars().all()

    items = []
    for ex in executions:
        steps_result = await db.execute(
            select(ExecutionStep).where(ExecutionStep.execution_id == ex.id)
        )
        steps = steps_result.scalars().all()
        items.append(ExecutionResponse(
            id=ex.id,
            workflow_id=ex.workflow_id,
            workflow_name=ex.workflow_name,
            status=ex.status,
            input_data=ex.input_data or {},
            output_data=ex.output_data,
            token_usage=ex.token_usage or {},
            started_at=ex.started_at,
            completed_at=ex.completed_at,
            error_message=ex.error_message,
            step_count=len(steps),
        ))

    return {"items": items, "total": len(items)}


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse, status_code=202)
async def execute_workflow(
    workflow_id: str,
    data: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """触发工作流执行（异步，返回 202）"""
    wf_result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = wf_result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")

    engine = _get_engine()
    engine.db = db
    execution = await engine.execute(
        workflow=workflow,
        input_text=data.input_text,
        variables=data.variables,
        user_id=user.sub,
        stream=data.stream,
    )

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
    """获取执行记录详情（含步骤数）"""
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
        created_at=execution.created_at,
        error_message=execution.error_message,
        step_count=len(steps),
    )


@router.get("/{execution_id}/stream")
async def stream_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """SSE 流式输出执行过程"""
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    streamer = _get_streamer()
    return StreamingResponse(
        streamer.subscribe(execution_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{execution_id}/steps")
async def list_execution_steps(execution_id: str, db: AsyncSession = Depends(get_db)):
    """获取执行步骤列表"""
    result = await db.execute(
        select(ExecutionStep).where(ExecutionStep.execution_id == execution_id).order_by(ExecutionStep.started_at)
    )
    steps = result.scalars().all()
    return {"items": [ExecutionStepResponse.model_validate(s) for s in steps]}


@router.post("/{execution_id}/pause", status_code=200)
async def pause_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """暂停执行"""
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    engine = _get_engine()
    engine.db = db
    await engine.pause(execution_id)
    return {"message": "执行已暂停", "execution_id": execution_id, "status": "paused"}


@router.post("/{execution_id}/resume", status_code=200)
async def resume_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """恢复执行"""
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    engine = _get_engine()
    engine.db = db
    await engine.resume(execution_id)
    return {"message": "执行已恢复", "execution_id": execution_id, "status": "running"}


@router.post("/{execution_id}/cancel", status_code=200)
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """取消执行"""
    result = await db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    engine = _get_engine()
    engine.db = db
    await engine.cancel(execution_id)
    return {"message": "执行已取消", "execution_id": execution_id, "status": "cancelled"}
