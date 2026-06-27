"""工具管理 API：注册、查询、测试工具"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.dependencies import get_db, get_current_user
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse, ToolTestRequest, ToolTestResponse

router = APIRouter(prefix="/api/v1/tools", tags=["工具管理"])


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(data: ToolCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """注册新工具"""
    tool = Tool(
        name=data.name,
        description=data.description,
        type=data.type,
        tool_schema=data.tool_schema,
        config=data.config,
        source=data.source,
        source_id=data.source_id,
        owner_id=user.sub,
    )
    db.add(tool)
    await db.flush()
    await db.refresh(tool)
    return tool


@router.get("")
async def list_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_filter: Optional[str] = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询工具列表（支持按类型过滤和分页）"""
    query = select(Tool).where(Tool.owner_id == user.sub)
    if type_filter:
        query = query.where(Tool.type == type_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Tool.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"items": [ToolResponse.model_validate(t) for t in items], "total": total or 0, "page": page, "page_size": page_size}


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """获取工具详情"""
    result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.owner_id == user.sub))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(tool_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """删除工具"""
    result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.owner_id == user.sub))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    await db.delete(tool)


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(tool_id: str, data: ToolTestRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """测试工具执行"""
    import time

    result = await db.execute(select(Tool).where(Tool.id == tool_id, Tool.owner_id == user.sub))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")

    try:
        from app.core.tool.registry import tool_registry

        registered_tool = tool_registry.get(tool_id)
        if not registered_tool:
            registered_tool = tool_registry.get_by_name(tool.name)

        if registered_tool:
            start = time.time()
            result_val = await registered_tool._arun(**data.input_data)
            elapsed = (time.time() - start) * 1000
            return ToolTestResponse(success=True, result=result_val, execution_time_ms=round(elapsed, 2))
        else:
            return ToolTestResponse(success=False, error=f"工具 '{tool.name}' 未注册到运行时", execution_time_ms=0)
    except Exception as e:
        return ToolTestResponse(success=False, error=str(e), execution_time_ms=0)
