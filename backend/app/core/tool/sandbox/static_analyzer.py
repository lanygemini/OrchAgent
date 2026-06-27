"""静态代码分析器：在沙箱执行前检查用户代码是否存在安全风险"""
import ast
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


# 禁止导入的模块
FORBIDDEN_MODULES = {
    "os", "subprocess", "sys", "shutil",
    "socket", "http", "urllib", "requests",
    "ctypes", "multiprocessing", "threading",
    "importlib", "builtins", "pickle", "marshal",
    "signal", "fcntl", "posix", "pty",
}

# 禁止调用的函数
FORBIDDEN_FUNCTIONS = {
    "eval", "exec", "compile", "open",
    "__import__", "getattr", "setattr",
    "globals", "locals", "vars",
}

# 允许的安全模块
ALLOWED_MODULES = {
    "json", "datetime", "re", "math", "statistics",
    "collections", "itertools", "functools",
    "textwrap", "string",
}

# 可疑代码模式
SUSPICIOUS_PATTERNS: List[Tuple[str, str]] = [
    (r"__[a-z]+__", "Suspicious dunder method access"),
    (r"chr\(\d+\)", "Suspicious char encoding bypass"),
    (r"decode\(.*\)", "Suspicious decode operation"),
]


@dataclass
class AnalysisResult:
    """代码分析结果"""
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StaticCodeAnalyzer:
    """静态分析用户提交的代码，检查是否使用危险模块/函数/模式"""

    def analyze(self, code: str) -> AnalysisResult:
        result = AnalysisResult()

        # AST 解析
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.passed = False
            result.errors.append(f"Syntax error: {e}")
            return result

        # 遍历 AST 节点
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                        result.errors.append(f"Forbidden module: {alias.name}")

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in FORBIDDEN_MODULES:
                    result.errors.append(f"Forbidden module: {node.module}")

            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_FUNCTIONS:
                    result.errors.append(f"Forbidden function: {node.func.id}")

        # 正则检测可疑模式
        for pattern, desc in SUSPICIOUS_PATTERNS:
            if re.search(pattern, code):
                result.warnings.append(f"{desc} (matches: {pattern})")

        if result.errors:
            result.passed = False

        return result


static_analyzer = StaticCodeAnalyzer()
