"""MCP 服务管理器：管理 MCP 服务器的生命周期（启动/停止/健康检查/工具发现）"""
import asyncio
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.tool.base import BaseTool

try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    MCP_CLIENT_AVAILABLE = False


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    transport: str
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    auth_type: str = "none"
    auth_config: Optional[Dict] = None


@dataclass
class MCPToolDef:
    """MCP 工具定义（来自 MCP 服务器暴露的工具元数据）"""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServerRuntime:
    """MCP 服务器运行时实例"""

    def __init__(self, server_id: str, config: MCPServerConfig):
        self.server_id = server_id
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._tools: List[MCPToolDef] = []
        self._healthy = False
        self._session: Optional[Any] = None  # 复用的 ClientSession
        self._session_context: Optional[Any] = None  # stdio_client 上下文

    async def start(self):
        """启动 MCP 服务器进程（stdio 模式）并发现工具"""
        if self.config.transport == "stdio" and self.config.command:
            self._process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                env={**self.config.env} if self.config.env else None,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._healthy = True

            # 启动后通过 MCP 协议发现工具
            await self.discover_tools_via_protocol()

    async def stop(self):
        """停止 MCP 服务器进程并清理 session"""
        # 清理复用的 session
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_context = None
            self._session = None

        if self._process:
            self._process.kill()
            await self._process.wait()
            self._process = None
            self._healthy = False

    async def health_check(self) -> bool:
        return self._healthy

    async def discover_tools(self) -> List[MCPToolDef]:
        """发现 MCP 服务器提供的工具列表"""
        return self._tools

    def set_tools(self, tools: List[MCPToolDef]):
        self._tools = tools

    async def discover_tools_via_protocol(self):
        """通过 MCP 协议 list_tools 发现工具并填充 _tools"""
        if not MCP_CLIENT_AVAILABLE or not self._process:
            return

        try:
            async with stdio_client(
                self.config.command,
                self.config.args or [],
                env=self.config.env or None,
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = []
                    for tool in result.tools:
                        tools.append(MCPToolDef(
                            name=tool.name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        ))
                    self._tools = tools
        except Exception:
            # 发现失败时保留空列表，不影响启动
            self._tools = []

    async def get_session(self):
        """获取复用的 MCP ClientSession（首次调用时创建，后续复用）"""
        if self._session is not None:
            return self._session

        if not MCP_CLIENT_AVAILABLE or not self.config.command:
            return None

        try:
            # 创建新的 stdio_client 连接用于复用
            ctx = stdio_client(
                self.config.command,
                self.config.args or [],
                env=self.config.env or None,
            )
            read, write = await ctx.__aenter__()
            session_ctx = ClientSession(read, write)
            self._session = await session_ctx.__aenter__()
            await self._session.initialize()
            self._session_context = ctx
            return self._session
        except Exception:
            return None


class MCPManager:
    """MCP 管理器：全局管理所有 MCP 服务器实例"""

    def __init__(self):
        self._servers: Dict[str, MCPServerRuntime] = {}
        self._tool_wrappers: Dict[str, "MCPToolWrapper"] = {}

    async def register_server(self, server_id: str, config: MCPServerConfig) -> MCPServerRuntime:
        """注册并启动 MCP 服务器"""
        runtime = MCPServerRuntime(server_id=server_id, config=config)
        await runtime.start()
        self._servers[server_id] = runtime
        return runtime

    async def unregister_server(self, server_id: str):
        """停止并注销 MCP 服务器"""
        if server_id in self._servers:
            await self._servers[server_id].stop()
            del self._servers[server_id]

    async def discover_tools(self, server_id: str) -> List[MCPToolDef]:
        """发现指定服务器的工具"""
        runtime = self._servers.get(server_id)
        if not runtime:
            return []
        return await runtime.discover_tools()

    async def health_check(self, server_id: str) -> bool:
        runtime = self._servers.get(server_id)
        if not runtime:
            return False
        return await runtime.health_check()

    def get_runtime(self, server_id: str) -> Optional[MCPServerRuntime]:
        return self._servers.get(server_id)

    def list_servers(self) -> List[MCPServerRuntime]:
        return list(self._servers.values())


mcp_manager = MCPManager()
