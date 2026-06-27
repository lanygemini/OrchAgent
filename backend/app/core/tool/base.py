from typing import Any, Optional, Type, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangChainBaseTool


class ToolInput(BaseModel):
    pass


class BaseTool(LangChainBaseTool):
    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = ToolInput
    tool_id: Optional[str] = None

    def _run(self, **kwargs: Any) -> str:
        raise NotImplementedError

    async def _arun(self, **kwargs: Any) -> str:
        raise NotImplementedError


class BuiltinTool(BaseTool):
    pass


class CustomTool(BaseTool):
    source_code: str = ""
    sandbox_config: Dict[str, Any] = {}


class CompositeTool(BaseTool):
    sub_tools: list = []

    async def _arun(self, **kwargs: Any) -> str:
        results = []
        for tool in self.sub_tools:
            result = await tool._arun(**kwargs)
            results.append(str(result))
        return "\n".join(results)
