"""提示注入防护：检测用户输入中的提示注入攻击，过滤输出中的敏感信息"""
import re
from typing import List, Tuple


class PromptGuard:
    """提示安全守卫 — 检测注入攻击并脱敏输出"""

    # 提示注入攻击模式
    INJECTION_PATTERNS: List[Tuple[str, str]] = [
        (r"(?i)ignore\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions|commands|directives)", "忽略指令攻击"),
        (r"(?i)forget\s+(all\s+)?(previous|prior|earlier)\s+(instructions|context)", "遗忘指令攻击"),
        (r"(?i)you\s+(are|were)\s+(an?\s+)?(AI|assistant|model|chatbot)", "角色越权尝试"),
        (r"(?i)system\s*(prompt|message|instruction)", "系统提示词泄露尝试"),
        (r"(?i)output\s+(your\s+)?(system\s+)?prompt", "提示词提取攻击"),
        (r"(?i)(reveal|show|print|display|leak)\s+(your\s+)?(system\s+)?(prompt|instructions)", "提示词泄露尝试"),
        (r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+", "输入中的凭证泄露"),
    ]

    # 需脱敏的敏感信息模式
    SENSITIVE_PATTERNS: List[Tuple[str, str]] = [
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API 密钥"),
        (r"AKIA[0-9A-Z]{16}", "AWS 访问密钥"),
        (r"\b\d{16}\b", "信用卡号"),
    ]

    @classmethod
    def scan_input(cls, text: str) -> List[str]:
        """扫描输入文本中的注入攻击模式，返回告警列表"""
        warnings = []
        for pattern, desc in cls.INJECTION_PATTERNS:
            if re.search(pattern, text):
                warnings.append(f"[{desc}] 在输入中检测到")
        return warnings

    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """脱敏输出文本中的敏感信息"""
        result = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            result = re.sub(pattern, f"[{replacement}_REDACTED]", result)
        return result

    @classmethod
    def is_safe_input(cls, text: str) -> bool:
        """判断输入是否安全（无注入攻击）"""
        warnings = cls.scan_input(text)
        return len(warnings) == 0


prompt_guard = PromptGuard()
