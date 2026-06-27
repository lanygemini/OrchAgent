import ast
import operator
from typing import Any, Type, Optional
from pydantic import BaseModel, Field

from app.core.tool.base import BuiltinTool


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="要计算的数学表达式（例如：'2 + 3 * 4'）")


_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorTool(BuiltinTool):
    name: str = "calculator"
    description: str = "安全计算数学表达式。支持 +、-、*、/、**、//、%"
    args_schema: Type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> str:
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = self._safe_eval(tree.body)
            return str(result)
        except Exception as e:
            return f"错误: {e}"

    async def _arun(self, expression: str) -> str:
        return self._run(expression)

    def _safe_eval(self, node):
        if isinstance(node, ast.Expression):
            return self._safe_eval(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            op_func = _SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            return op_func(self._safe_eval(node.left), self._safe_eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_func = _SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
            return op_func(self._safe_eval(node.operand))
        else:
            raise ValueError(f"不支持的表达式: {type(node).__name__}")
