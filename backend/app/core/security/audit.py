from datetime import datetime, timezone
from typing import Optional, Dict, Any


class AuditLogger:
    def __init__(self):
        self._entries: list = []

    def log(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address or "",
        }
        self._entries.append(entry)
        return entry

    def get_recent(self, limit: int = 100) -> list:
        return self._entries[-limit:]

    def get_by_user(self, user_id: str, limit: int = 50) -> list:
        return [e for e in self._entries if e["user_id"] == user_id][-limit:]


audit_logger = AuditLogger()
