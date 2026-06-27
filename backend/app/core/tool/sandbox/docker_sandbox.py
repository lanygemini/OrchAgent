import asyncio
import tempfile
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class SandboxResult:
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class DockerSandbox:
    def __init__(self, cpu_limit: float = 0.5, memory_limit_mb: int = 256, timeout_s: int = 10, network_enabled: bool = False):
        self.cpu_limit = cpu_limit
        self.memory_limit_mb = memory_limit_mb
        self.timeout_s = timeout_s
        self.network_enabled = network_enabled
        self._available = self._check_docker()

    def _check_docker(self) -> bool:
        return False

    async def execute(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> SandboxResult:
        if not self._available:
            return SandboxResult(success=False, output="", error="Docker 不可用")

        start = datetime.now(timezone.utc)
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm",
                "--memory", f"{self.memory_limit_mb}m",
                "--cpus", str(self.cpu_limit),
                "--network", "none" if not self.network_enabled else "bridge",
                "--read-only",
                "--tmpfs", "/tmp:size=16m",
                "-i",
                "python:3.12-slim",
                "python", "-c", code,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=repr(input_data).encode() if input_data else None),
                    timeout=self.timeout_s,
                )
            except asyncio.TimeoutError:
                proc.kill()
                elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                return SandboxResult(success=False, error=f"执行超时（{self.timeout_s} 秒）", execution_time_ms=elapsed)

            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            if proc.returncode == 0:
                return SandboxResult(success=True, output=stdout.decode().strip(), execution_time_ms=elapsed)
            else:
                return SandboxResult(success=False, output=stdout.decode().strip(), error=stderr.decode().strip(), execution_time_ms=elapsed)

        except FileNotFoundError:
            return SandboxResult(success=False, error="Docker 未安装或无法访问（沙箱模式）")


docker_sandbox = DockerSandbox()
