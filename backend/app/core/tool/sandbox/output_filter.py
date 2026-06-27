import re
from typing import Any, Dict


class OutputFilter:
    SENSITIVE_PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "[API_KEY_REDACTED]"),
        (r"AKIA[0-9A-Z]{16}", "[AWS_KEY_REDACTED]"),
        (r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "[JWT_REDACTED]"),
        (r"\b\d{16}\b", "[CREDIT_CARD_REDACTED]"),
        (r"(password|passwd|pwd|secret|token|api_key)\s*[:=]\s*\S+", r"\1=[REDACTED]"),
    ]

    def filter_text(self, text: str) -> str:
        result = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.filter_text(value)
            elif isinstance(value, dict):
                result[key] = self.filter_dict(value)
            else:
                result[key] = value
        return result


output_filter = OutputFilter()
