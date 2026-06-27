from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_db, get_current_user
from app.models.mcp import MCPServer
from app.schemas.mcp import MCPServerCreate, MCPServerResponse, MCPToolDef, MCPToolsResponse

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP 集成"])


@router.post("/servers", response_model=MCPServerResponse, status_code=201)
async def register_mcp_server(data: MCPServerCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    server = MCPServer(
        name=data.name,
        description=data.description,
        transport=data.transport,
        command=data.command,
        args=data.args,
        env=data.env,
        url=data.url,
        headers=data.headers,
        auth_type=data.auth_type,
        auth_config=data.auth_config,
        owner_id=user.sub,
    )
    db.add(server)
    await db.flush()
    await db.refresh(server)
    return server


@router.get("/servers")
async def list_mcp_servers(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.owner_id == user.sub).order_by(MCPServer.created_at.desc()))
    servers = result.scalars().all()
    return {"items": [MCPServerResponse.model_validate(s) for s in servers]}


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    return server


@router.get("/servers/{server_id}/tools", response_model=MCPToolsResponse)
async def discover_mcp_tools(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    return MCPToolsResponse(server_id=server_id, server_name=server.name, tools=[])


@router.post("/servers/{server_id}/import", status_code=200)
async def import_mcp_tools(server_id: str, tool_names: List[str], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    return {"message": f"正在从 {server.name} 导入 {len(tool_names)} 个工具（实现待完成）"}


@router.delete("/servers/{server_id}", status_code=204)
async def delete_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    await db.delete(server)


@router.get("/servers/{server_id}/health")
async def health_check_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    return {"server_id": server_id, "status": "unknown", "message": "MCP 健康检查（实现待完成）"}
