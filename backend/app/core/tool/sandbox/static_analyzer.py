import ast
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


FORBIDDEN_MODULES = {
    "os", "subprocess", "sys", "shutil",
    "socket", "http", "urllib", "requests",
    "ctypes", "multiprocessing", "threading",
    "importlib", "builtins", "pickle", "marshal",
    "signal", "fcntl", "posix", "pty",
}

FORBIDDEN_FUNCTIONS = {
    "eval", "exec", "compile", "open",
    "__import__", "getattr", "setattr",
    "globals", "locals", "vars",
}

ALLOWED_MODULES = {
    "json", "datetime", "re", "math", "statistics",
    "collections", "itertools", "functools",
    "textwrap", "string",
}

SUSPICIOUS_PATTERNS: List[Tuple[str, str]] = [
    (r"__[a-z]+__", "Suspicious dunder method access"),
    (r"chr\(\d+\)", "Suspicious char encoding bypass"),
    (r"decode\(.*\)", "Suspicious decode operation"),
]


@dataclass
class AnalysisResult:
    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StaticCodeAnalyzer:
    def analyze(self, code: str) -> AnalysisResult:
        result = AnalysisResult()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.passed = False
            result.errors.append(f"Syntax error: {e}")
            return result

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

        for pattern, desc in SUSPICIOUS_PATTERNS:
            if re.search(pattern, code):
                result.warnings.append(f"{desc} (matches: {pattern})")

        if result.errors:
            result.passed = False

        return result


static_analyzer = StaticCodeAnalyzer()
