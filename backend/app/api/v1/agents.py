from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse, AgentTestRequest
from app.core.prompts import get_default_system_prompt

router = APIRouter(prefix="/api/v1/agents", tags=["Agent 管理"])


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    system_prompt = data.system_prompt
    if not system_prompt:
        system_prompt = get_default_system_prompt(data.role)

    agent = Agent(
        name=data.name,
        role=data.role,
        description=data.description,
        system_prompt=system_prompt,
        llm_provider=data.llm_provider,
        model_name=data.model_name,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        enable_memory=data.enable_memory,
        memory_window=data.memory_window,
        memory_policy=data.memory_policy,
        owner_id=user.sub,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(Agent).where(Agent.owner_id == user.sub)
    if search:
        query = query.where(Agent.name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.order_by(Agent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return AgentListResponse(items=[AgentResponse.model_validate(a) for a in items], total=total or 0, page=page, page_size=page_size)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_id == user.sub))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_id == user.sub))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.flush()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_id == user.sub))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    await db.delete(agent)


@router.post("/{agent_id}/test")
async def test_agent(agent_id: str, data: AgentTestRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.owner_id == user.sub))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return {"message": "Agent 测试端点（LLM 集成待实现）", "agent_id": agent_id, "input": data.input_text, "stream": data.stream}
