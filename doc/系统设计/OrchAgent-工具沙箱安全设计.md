# OrchAgent — 工具沙箱安全设计

---

## 一、问题定义

三种工具类型的安全风险：

| 工具类型 | 风险 |
|---------|------|
| 内置工具 | 低 — 由我们开发，可控 |
| MCP 工具 | 中 — 由 MCP Server 开发者控制 |
| 自定义工具 | 高 — 用户可编写任意代码 |

---

## 二、分层防护架构

```
                        用户提交的代码
                              │
                    ┌─────────▼─────────┐
                    │  静态代码分析      │
                    │  (AST 检查)       │  <- 第1层：语法级
                    │  黑名单关键字      │
                    └─────────┬─────────┘
                              │ 通过
                    ┌─────────▼─────────┐
                    │  Docker 沙箱执行   │
                    │  CPU: 0.5核      │  <- 第2层：容器级
                    │  Mem: 256MB      │
                    │  Time: 10s       │
                    │  No network      │
                    │  Read-only FS    │
                    └─────────┬─────────┘
                              │ 执行结果
                    ┌─────────▼─────────┐
                    │  结果安全过滤      │  <- 第3层：输出级
                    │  脱敏检查          │
                    └───────────────────┘
```

---

## 三、静态代码分析

```python
import ast

class StaticCodeAnalyzer:
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

    SUSPICIOUS_PATTERNS = [
        (r"__[a-z]+__", "疑似内置魔术方法调用"),
        (r"chr\(\d+\)", "疑似字符编码绕过"),
        (r"decode\(.*\)", "疑似编码操作"),
    ]

    ALLOWED_MODULES = {
        "json", "datetime", "re", "math", "statistics",
        "collections", "itertools", "functools",
        "textwrap", "string",
    }

    def analyze(self, code: str) -> AnalysisResult:
        errors = []
        warnings = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return AnalysisResult(safe=False, errors=[f"语法错误: {e}"])

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.FORBIDDEN_MODULES:
                        errors.append(f"禁止导入模块: {alias.name}")

            if isinstance(node, ast.ImportFrom):
                if node.module in self.FORBIDDEN_MODULES:
                    errors.append(f"禁止导入模块: {node.module}")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_FUNCTIONS:
                        errors.append(f"禁止调用函数: {node.func.id}()")

            if isinstance(node, ast.Attribute):
                full_name = self._get_full_attr_name(node)
                for forbidden in self.FORBIDDEN_MODULES:
                    if full_name.startswith(forbidden + "."):
                        errors.append(f"禁止访问: {full_name}")

        for pattern, message in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, code):
                warnings.append(f"{message}: 匹配 {pattern}")

        return AnalysisResult(
            safe=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

---

## 四、Docker 沙箱执行

```python
import docker
import tempfile
from pathlib import Path

class DockerSandbox:
    SANDBOX_IMAGE = "orchagent-sandbox:latest"
    EXECUTION_TIMEOUT = 10
    MAX_OUTPUT_SIZE = 100 * 1024

    def __init__(self):
        self.client = docker.from_env()

    async def execute(self, code: str, input_data: str, tool_id: str):
        with tempfile.TemporaryDirectory(prefix=f"sandbox_{tool_id}_") as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "tool.py").write_text(self._wrap_code(code))
            (tmpdir / "input.json").write_text(input_data)
            (tmpdir / "Dockerfile").write_text(self._generate_dockerfile())

            image, _ = self.client.images.build(
                path=str(tmpdir),
                tag=f"sandbox_{tool_id}:latest",
                rm=True,
            )

            try:
                container = self.client.containers.run(
                    image=image.id,
                    command=["python", "/app/tool.py"],
                    detach=True,
                    read_only=True,
                    network_mode="none",
                    mem_limit="256m",
                    nano_cpus=500_000_000,
                    pids_limit=50,
                    security_opt=["no-new-privileges:true"],
                    cap_drop=["ALL"],
                    tmpfs={"/tmp": "size=10M,mode=1777"},
                )

                exit_code = container.wait(timeout=self.EXECUTION_TIMEOUT)
                logs = container.logs(stdout=True, stderr=True)[:self.MAX_OUTPUT_SIZE]
                container.remove(force=True)
                self.client.images.remove(image.id, force=True)

                return SandboxResult(
                    success=exit_code["StatusCode"] == 0,
                    stdout=logs.decode(errors="replace"),
                )

            except docker.errors.APIError as e:
                try:
                    container.remove(force=True)
                except:
                    pass
                raise

    def _wrap_code(self, user_code: str) -> str:
        return f'''
import json, sys, traceback

with open("/app/input.json", "r") as f:
    input_data = json.load(f)

{user_code}

try:
    result = main(input_data)
    print(json.dumps({{"status": "ok", "result": result}}))
except Exception as e:
    print(json.dumps({{
        "status": "error",
        "error": str(e),
        "traceback": traceback.format_exc()[:500]
    }}))
'''

    def _generate_dockerfile(self) -> str:
        return '''
FROM python:3.12-slim
RUN useradd -m -s /bin/bash sandbox
WORKDIR /app
COPY tool.py /app/
COPY input.json /app/
RUN chown -R sandbox:sandbox /app && chmod -R 444 /app
USER sandbox
CMD ["python", "/app/tool.py"]
'''
```

---

## 五、输出安全过滤

```python
class OutputSanitizer:
    SENSITIVE_PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "[API_KEY_REDACTED]"),
        (r"AKID[a-zA-Z0-9]{20,}", "[SECRET_REDACTED]"),
        (r"password\s*[:=]\s*\S+", "password=[REDACTED]"),
        (r"-----BEGIN.*PRIVATE KEY-----[\s\S]*?-----END", "[PRIVATE_KEY_REDACTED]"),
        (r"\d{15,19}", "[ID_REDACTED]"),
        (r"1[3-9]\d{9}", "[PHONE_REDACTED]"),
    ]

    def sanitize(self, output: str) -> str:
        if len(output) > 100 * 1024:
            output = output[:100 * 1024]
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            output = re.sub(pattern, replacement, output)
        return output
```

---

## 六、MCP 工具的安全策略

```python
class MCPSecurityPolicy:
    SERVER_SECURITY_CONFIGS = {
        "database": {
            "allowed_operations": ["SELECT", "DESCRIBE", "SHOW"],
            "require_readonly": True,
            "timeout_seconds": 10,
        },
        "filesystem": {
            "allowed_paths": ["/data/shared", "/tmp"],
            "disallowed_paths": ["/etc", "/root", "/home"],
            "max_file_size": 10 * 1024 * 1024,
        },
        "network": {
            "allowed_domains": ["api.github.com", "api.openai.com"],
            "allowed_ports": [80, 443],
            "disallowed_ips": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        },
    }
```

---

## 七、自定义工具生命周期

```
创建 -> 静态分析 -> 审核(可选) -> 测试 -> 启用 -> 运行时(沙箱) -> 监控 -> 禁用/删除
```

---

## 八、安全开关配置

```python
class SecurityConfig:
    SANDBOX_MODE = os.getenv("SANDBOX_MODE", "docker")     # docker | process | none
    ENABLE_CUSTOM_TOOLS = os.getenv("ENABLE_CUSTOM_TOOLS", "true") == "true"
    CUSTOM_TOOL_REQUIRE_REVIEW = os.getenv("CUSTOM_TOOL_REQUIRE_REVIEW", "false") == "true"
    SANDBOX_DEFAULT_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "10"))
    SANDBOX_DEFAULT_MEMORY_MB = int(os.getenv("SANDBOX_MEMORY_MB", "256"))
    SANDBOX_DISABLE_NETWORK = os.getenv("SANDBOX_DISABLE_NETWORK", "true") == "true"
    ENABLE_OUTPUT_SANITIZATION = os.getenv("ENABLE_OUTPUT_SANITIZATION", "true") == "true"
    MAX_OUTPUT_SIZE_KB = int(os.getenv("MAX_OUTPUT_SIZE_KB", "100"))
```
