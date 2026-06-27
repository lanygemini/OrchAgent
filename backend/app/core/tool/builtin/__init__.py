"""注册所有内置工具到全局注册表"""
from app.core.tool.registry import tool_registry
from app.core.tool.builtin.calculator import CalculatorTool
from app.core.tool.builtin.datetime_tool import DateTimeTool


def register_builtin_tools():
    """注册所有内置工具（启动时调用）"""
    calculator = CalculatorTool()
    calculator.tool_id = "builtin_calculator"
    tool_registry.register(calculator)

    dt_tool = DateTimeTool()
    dt_tool.tool_id = "builtin_datetime"
    tool_registry.register(dt_tool)


builtin_tools_registered = False


def ensure_builtin_tools():
    """确保内置工具已注册（幂等）"""
    global builtin_tools_registered
    if not builtin_tools_registered:
        register_builtin_tools()
        builtin_tools_registered = True
