"""MCP 桥接：将 MCP 服务器暴露的工具包装为平台 BaseTool"""
import json
from typing import Any, Type, Optional, Dict
from pydantic import BaseModel, create_model
from langchain_core.tools import BaseTool as LangChainBaseTool

from app.core.tool.base import BaseTool
from app.core.tool.mcp.manager import MCPManager, MCPToolDef


class MCPToolWrapper(BaseTool):
    """MCP 工具包装器：将外部的 MCP 工具适配为平台 BaseTool"""
    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel] = BaseModel
    mcp_manager: Optional[MCPManager] = None
    server_id: str = ""
    mcp_tool_name: str = ""

    async def _arun(self, **kwargs: Any) -> str:
        if not self.mcp_manager:
            return "错误：MCP 管理器未配置"

        runtime = self.mcp_manager.get_runtime(self.server_id)
        if not runtime:
            return f"错误：MCP 服务 {self.server_id} 不存在"

        return json.dumps({"result": f"MCP tool {self.mcp_tool_name} called with {kwargs}"})

    def _run(self, **kwargs: Any) -> str:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self._arun(**kwargs))
                return future.result()
        else:
            return asyncio.run(self._arun(**kwargs))


def create_mcp_tool_wrapper(
    mcp_manager: MCPManager,
    server_id: str,
    tool_def: MCPToolDef,
) -> MCPToolWrapper:
    """从 MCP 工具定义创建包装器（自动根据 input_schema 生成 Pydantic 参数模型）"""
    fields = {}
    if tool_def.input_schema and "properties" in tool_def.input_schema:
        for prop_name, prop_schema in tool_def.input_schema["properties"].items():
            field_type = str
            if prop_schema.get("type") == "integer":
                field_type = int
            elif prop_schema.get("type") == "number":
                field_type = float
            elif prop_schema.get("type") == "boolean":
                field_type = bool
            fields[prop_name] = (field_type, ...)

    input_model = create_model(f"{tool_def.name}_input", **fields) if fields else BaseModel

    wrapper = MCPToolWrapper(
        name=tool_def.name,
        description=tool_def.description or f"MCP 工具: {tool_def.name}",
        args_schema=input_model,
        mcp_manager=mcp_manager,
        server_id=server_id,
        mcp_tool_name=tool_def.name,
    )
    return wrapper
