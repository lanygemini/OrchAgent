"""内置日期时间工具：获取当前 UTC 时间并按指定格式输出"""
from datetime import datetime, timezone
from typing import Type, Optional
from pydantic import BaseModel, Field

from app.core.tool.base import BuiltinTool


class DateTimeInput(BaseModel):
    format: str = Field("%Y-%m-%d %H:%M:%S", description="输出格式（Python strftime 格式）")


class DateTimeTool(BuiltinTool):
    """获取当前 UTC 日期和时间"""
    name: str = "datetime"
    description: str = "获取当前日期和时间，可按指定格式输出"
    args_schema: Type[BaseModel] = DateTimeInput

    def _run(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.now(timezone.utc).strftime(format)

    async def _arun(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return self._run(format)
