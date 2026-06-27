from typing import Dict, List, Optional
from app.core.tool.base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._agent_tool_map: Dict[str, List[str]] = {}

    def register(self, tool: BaseTool) -> str:
        key = tool.tool_id or tool.name
        self._tools[key] = tool
        return key

    def unregister(self, tool_id: str):
        self._tools.pop(tool_id, None)
        for agent_id in list(self._agent_tool_map.keys()):
            self._agent_tool_map[agent_id] = [t for t in self._agent_tool_map[agent_id] if t != tool_id]

    def get(self, tool_id: str) -> Optional[BaseTool]:
        return self._tools.get(tool_id)

    def get_by_name(self, name: str) -> Optional[BaseTool]:
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def list_all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_for_agent(self, agent_id: str) -> List[BaseTool]:
        tool_ids = self._agent_tool_map.get(agent_id, [])
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]

    def bind_to_agent(self, agent_id: str, tool_ids: List[str]):
        self._agent_tool_map[agent_id] = tool_ids

    def unbind_from_agent(self, agent_id: str):
        self._agent_tool_map.pop(agent_id, None)


tool_registry = ToolRegistry()
