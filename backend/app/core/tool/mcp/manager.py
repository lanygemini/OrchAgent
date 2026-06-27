import asyncio
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.tool.base import BaseTool


@dataclass
class MCPServerConfig:
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
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServerRuntime:
    def __init__(self, server_id: str, config: MCPServerConfig):
        self.server_id = server_id
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._tools: List[MCPToolDef] = []
        self._healthy = False

    async def start(self):
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

    async def stop(self):
        if self._process:
            self._process.kill()
            await self._process.wait()
            self._process = None
            self._healthy = False

    async def health_check(self) -> bool:
        return self._healthy

    async def discover_tools(self) -> List[MCPToolDef]:
        return self._tools

    def set_tools(self, tools: List[MCPToolDef]):
        self._tools = tools


class MCPManager:
    def __init__(self):
        self._servers: Dict[str, MCPServerRuntime] = {}
        self._tool_wrappers: Dict[str, "MCPToolWrapper"] = {}

    async def register_server(self, server_id: str, config: MCPServerConfig) -> MCPServerRuntime:
        runtime = MCPServerRuntime(server_id=server_id, config=config)
        await runtime.start()
        self._servers[server_id] = runtime
        return runtime

    async def unregister_server(self, server_id: str):
        if server_id in self._servers:
            await self._servers[server_id].stop()
            del self._servers[server_id]

    async def discover_tools(self, server_id: str) -> List[MCPToolDef]:
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
