"""MCP 集成 API：注册 MCP 服务器、发现工具、导入工具、健康检查"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.dependencies import get_db, get_current_user
from app.models.mcp import MCPServer
from app.models.tool import Tool
from app.schemas.mcp import MCPServerCreate, MCPServerResponse, MCPToolDef, MCPToolsResponse
from app.core.tool.mcp.manager import mcp_manager, MCPServerConfig, MCPToolDef as MgrToolDef
from app.core.tool.registry import tool_registry
from app.core.tool.mcp.bridge import create_mcp_tool_wrapper

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP 集成"])


async def _get_mcp_server(server_id: str, db: AsyncSession, user) -> MCPServer:
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id, MCPServer.owner_id == user.sub))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP 服务不存在")
    return server


def _server_to_config(server: MCPServer) -> MCPServerConfig:
    return MCPServerConfig(
        name=server.name,
        transport=server.transport,
        command=server.command,
        args=server.args,
        env=server.env,
        url=server.url,
        headers=server.headers,
        auth_type=server.auth_type,
        auth_config=server.auth_config,
    )


@router.post("/servers", response_model=MCPServerResponse, status_code=201)
async def register_mcp_server(data: MCPServerCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """注册 MCP 服务器"""
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
    """列出已注册的 MCP 服务器"""
    result = await db.execute(select(MCPServer).where(MCPServer.owner_id == user.sub).order_by(MCPServer.created_at.desc()))
    servers = result.scalars().all()
    return {"items": [MCPServerResponse.model_validate(s) for s in servers]}


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """获取 MCP 服务器详情"""
    return await _get_mcp_server(server_id, db, user)


@router.get("/servers/{server_id}/tools", response_model=MCPToolsResponse)
async def discover_mcp_tools(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """发现 MCP 服务器提供的工具列表"""
    server = await _get_mcp_server(server_id, db, user)

    config = _server_to_config(server)
    await mcp_manager.register_server(server_id, config)
    discovered = await mcp_manager.discover_tools(server_id)

    tools = [MCPToolDef(name=t.name, description=t.description, input_schema=t.input_schema) for t in discovered]
    return MCPToolsResponse(server_id=server_id, server_name=server.name, tools=tools)


@router.post("/servers/{server_id}/import", status_code=200)
async def import_mcp_tools(server_id: str, tool_names: List[str], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """从 MCP 服务器导入工具到平台"""
    server = await _get_mcp_server(server_id, db, user)

    discovered = await mcp_manager.discover_tools(server_id)
    discovered_map = {t.name: t for t in discovered}

    imported = []
    for tname in tool_names:
        if tname not in discovered_map:
            continue
        tdef = discovered_map[tname]

        existing = await db.execute(select(Tool).where(Tool.name == tname, Tool.owner_id == user.sub))
        if existing.scalar_one_or_none():
            continue

        tool = Tool(
            name=tname,
            description=tdef.description or f"MCP 工具: {tname}",
            type="mcp",
            tool_schema=tdef.input_schema,
            config={},
            source="mcp",
            source_id=server_id,
            owner_id=user.sub,
        )
        db.add(tool)
        await db.flush()

        wrapper = create_mcp_tool_wrapper(mcp_manager, server_id, MgrToolDef(
            name=tdef.name, description=tdef.description, input_schema=tdef.input_schema,
        ))
        wrapper.tool_id = tool.id
        tool_registry.register(wrapper)

        imported.append(tname)

    await db.commit()
    return {"message": f"已从 {server.name} 导入 {len(imported)} 个工具", "tools": imported}


@router.delete("/servers/{server_id}", status_code=204)
async def delete_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """删除 MCP 服务器"""
    server = await _get_mcp_server(server_id, db, user)
    await mcp_manager.unregister_server(server_id)
    await db.delete(server)


@router.get("/servers/{server_id}/health")
async def health_check_mcp_server(server_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """检查 MCP 服务器健康状态"""
    server = await _get_mcp_server(server_id, db, user)

    healthy = await mcp_manager.health_check(server_id)
    status = "healthy" if healthy else "unhealthy"
    return {"server_id": server_id, "status": status, "message": f"MCP 服务状态: {status}"}
