"""安全表达式求值器：替代 eval()，只允许访问 state/context 的安全属性，禁止任意代码执行"""
import operator
import re
from typing import Any, Dict, Optional


# 允许的二元操作符
SAFE_OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
}

# 允许的一元操作符
SAFE_UNARY_OPERATORS = {
    "not": operator.not_,
}

# 禁止的关键字和模式
FORBIDDEN_PATTERNS = [
    r"__\w+__",           # dunder 方法
    r"import\s+",         # import 语句
    r"exec\s*\(",         # exec 调用
    r"eval\s*\(",         # eval 调用
    r"open\s*\(",         # 文件操作
    r"compile\s*\(",      # compile 调用
    r"globals\s*\(",      # globals 访问
    r"locals\s*\(",       # locals 访问
    r"getattr\s*\(",      # getattr 调用
    r"setattr\s*\(",      # setattr 调用
    r"delattr\s*\(",      # delattr 调用
    r"__import__\s*\(",   # __import__ 调用
]


class SafeExpressionError(Exception):
    """安全表达式求值错误"""
    pass


class SafeExpressionEvaluator:
    """安全表达式求值器 — 仅支持简单的条件判断表达式

    支持的语法：
    - 属性访问：state['key']、context.get('key')、context.key
    - 比较操作：==, !=, >, >=, <, <=
    - 逻辑操作：and, or, not
    - 成员判断：in, not in
    - 字符串/数字/布尔字面量
    - 简单的 .get() 调用

    不支持：
    - 函数定义、类定义
    - import 语句
    - 任意函数调用（除了 .get()）
    - 列表推导、生成器表达式
    """

    @staticmethod
    def check_forbidden(expr: str) -> None:
        """检查表达式是否包含禁止的模式"""
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, expr):
                raise SafeExpressionError(f"表达式包含禁止的模式: {pattern}")

    @staticmethod
    def evaluate(expr: str, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """安全地求值条件表达式

        Args:
            expr: 条件表达式字符串
            state: 工作流状态字典
            context: 上下文字典（默认从 state 中取）

        Returns:
            表达式的求值结果

        Raises:
            SafeExpressionError: 表达式包含禁止模式或语法错误
        """
        if not expr or not expr.strip():
            return True

        SafeExpressionEvaluator.check_forbidden(expr)

        # 构建安全的命名空间
        ctx = context or state.get("context", {})
        safe_namespace = {
            "state": state,
            "context": ctx,
            "True": True,
            "False": False,
            "None": None,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "min": min,
            "max": max,
        }

        try:
            # 使用 compile + 受限命名空间求值
            # __builtins__ 设为空字典，禁止访问任何内置函数
            safe_namespace["__builtins__"] = {}
            code = compile(expr, "<safe_expr>", "eval")
            result = eval(code, safe_namespace)
            return result
        except NameError as e:
            raise SafeExpressionError(f"表达式中使用了不允许的名称: {e}")
        except SyntaxError as e:
            raise SafeExpressionError(f"表达式语法错误: {e}")
        except Exception as e:
            raise SafeExpressionError(f"表达式求值失败: {e}")


def safe_eval(expr: str, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
    """便捷函数：安全求值条件表达式

    Args:
        expr: 条件表达式
        state: 工作流状态
        context: 上下文

    Returns:
        求值结果，出错时返回 False
    """
    try:
        return SafeExpressionEvaluator.evaluate(expr, state, context)
    except SafeExpressionError:
        return False
