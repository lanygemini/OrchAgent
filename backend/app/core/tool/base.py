"""工具基类：继承 LangChain BaseTool，扩展内置 / 自定义 / 复合三种类型"""
from typing import Any, Optional, Type, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangChainBaseTool


class ToolInput(BaseModel):
    """工具输入参数基类"""
    pass


class BaseTool(LangChainBaseTool):
    """平台工具基类（扩展 LangChain BaseTool 添加 tool_id 字段）"""
    name: str = ""
    description: str = ""
    args_schema: Optional[Type[BaseModel]] = ToolInput
    tool_id: Optional[str] = None

    def _run(self, **kwargs: Any) -> str:
        raise NotImplementedError

    async def _arun(self, **kwargs: Any) -> str:
        raise NotImplementedError


class BuiltinTool(BaseTool):
    """内置工具（如计算器、日期时间等）"""
    pass


class CustomTool(BaseTool):
    """自定义工具（用户上传的代码，在沙箱中执行）"""
    source_code: str = ""
    sandbox_config: Dict[str, Any] = {}


class CompositeTool(BaseTool):
    """复合工具：组合多个子工具依次执行"""
    sub_tools: list = []

    async def _arun(self, **kwargs: Any) -> str:
        results = []
        for tool in self.sub_tools:
            result = await tool._arun(**kwargs)
            results.append(str(result))
        return "\n".join(results)
