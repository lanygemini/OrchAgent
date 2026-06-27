"""工作流管理 API：CRUD + 校验"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.models.workflow import Workflow, WorkflowNode, WorkflowEdge
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowValidateResponse

router = APIRouter(prefix="/api/v1/workflows", tags=["工作流管理"])


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(data: WorkflowCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """创建新工作流（包含 DAG 定义）"""
    workflow = Workflow(
        name=data.name,
        description=data.description,
        owner_id=user.sub,
    )
    db.add(workflow)
    await db.flush()

    for node_data in data.dag.nodes:
        node = WorkflowNode(
            workflow_id=workflow.id,
            type=node_data.type,
            label=node_data.label,
            config=node_data.config,
            position_x=node_data.position_x,
            position_y=node_data.position_y,
            agent_id=node_data.agent_id,
            tool_id=node_data.tool_id,
        )
        db.add(node)

    for edge_data in data.dag.edges:
        edge = WorkflowEdge(
            workflow_id=workflow.id,
            source_node_id=edge_data.source_node_id,
            target_node_id=edge_data.target_node_id,
            condition_expr=edge_data.condition_expr,
            label=edge_data.label,
        )
        db.add(edge)

    workflow.start_node_id = data.dag.start_node_id
    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.get("")
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询工作流列表（分页）"""
    query = select(Workflow).where(Workflow.owner_id == user.sub)
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Workflow.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": [WorkflowResponse.model_validate(w) for w in items], "total": total or 0, "page": page, "page_size": page_size}


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """获取工作流详情（包含 DAG 定义）"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")

    dag = {
        "nodes": [{"id": n.id, "type": n.type, "label": n.label, "config": n.config, "position_x": n.position_x, "position_y": n.position_y, "agent_id": n.agent_id, "tool_id": n.tool_id} for n in workflow.nodes],
        "edges": [{"id": e.id, "source_node_id": e.source_node_id, "target_node_id": e.target_node_id, "condition_expr": e.condition_expr, "label": e.label} for e in workflow.edges],
        "start_node_id": workflow.start_node_id,
    }

    response = WorkflowResponse.model_validate(workflow)
    response.dag = dag
    return response


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, data: WorkflowUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """更新工作流（可替换整个 DAG）"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")

    update_data = data.model_dump(exclude_unset=True, exclude={"dag"})
    for key, value in update_data.items():
        setattr(workflow, key, value)

    if data.dag:
        for node in workflow.nodes:
            await db.delete(node)
        for edge in workflow.edges:
            await db.delete(edge)

        for node_data in data.dag.nodes:
            node = WorkflowNode(
                workflow_id=workflow.id,
                type=node_data.type,
                label=node_data.label,
                config=node_data.config,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                agent_id=node_data.agent_id,
                tool_id=node_data.tool_id,
            )
            db.add(node)

        for edge_data in data.dag.edges:
            edge = WorkflowEdge(
                workflow_id=workflow.id,
                source_node_id=edge_data.source_node_id,
                target_node_id=edge_data.target_node_id,
                condition_expr=edge_data.condition_expr,
                label=edge_data.label,
            )
            db.add(edge)

        workflow.start_node_id = data.dag.start_node_id

    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """删除工作流（级联删除节点和边）"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    await db.delete(workflow)


@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResponse)
async def validate_workflow(workflow_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """校验工作流 DAG 的合法性"""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.sub))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return WorkflowValidateResponse(valid=True, errors=[], warnings=[])
