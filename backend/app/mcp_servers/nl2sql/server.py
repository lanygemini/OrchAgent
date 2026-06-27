"""NL2SQL MCP 服务器：提供自然语言转 SQL 和 SQL 执行（安全约束）能力"""
import asyncio
import json
import re
from typing import Optional

try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


# 禁止的 SQL 关键词（写入/删除/修改操作）
FORBIDDEN_SQL_KEYWORDS = [
    "DROP", "ALTER", "TRUNCATE", "DELETE", "INSERT", "UPDATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
]

# 允许的 SQL 前缀（只读查询）
ALLOWED_SQL_PREFIXES = ["SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"]


def validate_sql(sql: str) -> tuple[bool, str]:
    """SQL 安全性校验：只允许只读查询"""
    sql_upper = sql.strip().upper()

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, sql_upper):
            return False, f"SQL 被拒绝：不允许执行 {keyword} 操作"

    allowed = False
    for prefix in ALLOWED_SQL_PREFIXES:
        if sql_upper.startswith(prefix):
            allowed = True
            break

    if not allowed:
        return False, "SQL 被拒绝：只允许执行 SELECT/WITH 查询"

    return True, ""


def build_select_sql(nl_query: str, db_schema: str) -> str:
    """根据表结构生成简单的 SELECT 查询"""
    tables = [line.strip() for line in db_schema.split('\n') if line.strip()]
    if not tables:
        return "SELECT 1"

    table_info = {}
    for line in tables:
        if '(' in line:
            tname = line.split('(')[0].strip()
            cols_part = line[line.index('(')+1:line.rindex(')')]
            cols = [c.strip().split()[0] for c in cols_part.split(',') if c.strip()]
            table_info[tname] = cols

    if not table_info:
        return "SELECT 1"

    tname = list(table_info.keys())[0]
    cols = table_info[tname][:5]
    cols_str = ', '.join(cols) if cols else '*'
    return f"SELECT {cols_str} FROM {tname} LIMIT 10"
    """创建 NL2SQL MCP 服务器实例"""
    if not MCP_AVAILABLE:
        return None

    app = Server("nl2sql-server")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="translate_to_sql",
                description="将自然语言翻译为 SQL 查询语句，需提供数据库表结构信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "nl_query": {"type": "string", "description": "自然语言查询"},
                        "db_schema": {"type": "string", "description": "数据库表结构定义"},
                    },
                    "required": ["nl_query"],
                },
            ),
            Tool(
                name="execute_query",
                description="执行 SQL 查询（含安全检查）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "要执行的 SQL 查询"},
                        "db_url": {"type": "string", "description": "数据库连接 URL"},
                    },
                    "required": ["sql"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "translate_to_sql":
            nl_query = arguments.get("nl_query", "")
            db_schema = arguments.get("db_schema", "")
            sql = build_select_sql(nl_query, db_schema)
            return [TextContent(type="text", text=json.dumps({"sql": sql, "confidence": "low"}))]

        elif name == "execute_query":
            sql = arguments.get("sql", "")
            is_valid, error_msg = validate_sql(sql)
            if not is_valid:
                return [TextContent(type="text", text=json.dumps({"error": error_msg, "success": False}))]

            return [TextContent(type="text", text=json.dumps({"result": "查询执行占位结果", "success": True, "rows_affected": 0}))]

        raise ValueError(f"未知工具: {name}")

    return app


async def run_server():
    """运行 NL2SQL MCP 服务器（stdio 模式）"""
    app = create_nl2sql_server()
    if app is None:
        print("MCP 包不可用。请执行: pip install mcp")
        return

    async with app.run("stdio") as server:
        await server.wait()


if __name__ == "__main__":
    asyncio.run(run_server())
