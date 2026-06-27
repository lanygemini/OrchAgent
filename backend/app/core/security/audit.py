"""审计日志：记录用户操作行为（内存存储，后续可扩展为 DB 持久化）"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class AuditLogger:
    """审计日志记录器 — 记录用户的关键操作"""

    def __init__(self, max_in_memory: int = 1000):
        self._entries: List[Dict] = []
        self._max_in_memory = max_in_memory

    def log(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """记录一条审计日志"""
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
        if len(self._entries) > self._max_in_memory:
            self._entries = self._entries[-self._max_in_memory:]
        return entry

    def get_recent(self, limit: int = 100) -> List[Dict]:
        """获取最近的操作记录"""
        return self._entries[-limit:]

    def get_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """查询指定用户的操作记录"""
        return [e for e in self._entries if e["user_id"] == user_id][-limit:]

    def get_by_resource(self, resource_type: str, resource_id: str, limit: int = 50) -> List[Dict]:
        """查询指定资源的操作记录"""
        return [e for e in self._entries
                if e["resource_type"] == resource_type and e["resource_id"] == resource_id][-limit:]


audit_logger = AuditLogger()
