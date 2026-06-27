"""工具注册中心：管理所有注册的工具及其与 Agent 的绑定关系"""
from typing import Dict, List, Optional
from app.core.tool.base import BaseTool


class ToolRegistry:
    """全局工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}           # tool_id → BaseTool
        self._agent_tool_map: Dict[str, List[str]] = {}  # agent_id → [tool_id, ...]

    def register(self, tool: BaseTool) -> str:
        """注册工具到全局注册表"""
        key = tool.tool_id or tool.name
        self._tools[key] = tool
        return key

    def unregister(self, tool_id: str):
        """注销工具"""
        self._tools.pop(tool_id, None)
        for agent_id in list(self._agent_tool_map.keys()):
            self._agent_tool_map[agent_id] = [t for t in self._agent_tool_map[agent_id] if t != tool_id]

    def get(self, tool_id: str) -> Optional[BaseTool]:
        """根据 ID 获取工具"""
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> Optional[BaseTool]:
        """根据名称查找工具"""
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def list_all(self) -> List[BaseTool]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def get_for_agent(self, agent_id: str) -> List[BaseTool]:
        """获取绑定给指定 Agent 的工具列表"""
        tool_ids = self._agent_tool_map.get(agent_id, [])
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]

    def bind_to_agent(self, agent_id: str, tool_ids: List[str]):
        """将工具列表绑定到 Agent"""
        self._agent_tool_map[agent_id] = tool_ids

    def unbind_from_agent(self, agent_id: str):
        """解绑 Agent 的所有工具"""
        self._agent_tool_map.pop(agent_id, None)


tool_registry = ToolRegistry()
