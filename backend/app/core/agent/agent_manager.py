"""Agent 管理器：创建 / 缓存 / 获取 AgentRuntime，驱动 Agent 的 invoke / stream"""
from typing import Optional, AsyncIterator, Dict, Any, List
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.agent.llm_factory import LLMFactory, LLMUsageCallback
from app.core.prompts import get_default_system_prompt
from app.models.agent import Agent as AgentModel


@dataclass
class AgentConfig:
    """Agent 运行时配置"""
    name: str
    role: str
    llm_provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    enable_memory: bool = True
    memory_window: int = 10
    memory_policy: str = "private"


@dataclass
class AgentResponse:
    """Agent 调用响应"""
    content: str
    agent_id: str
    token_usage: Dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})


@dataclass
class Chunk:
    """流式响应块"""
    content: str
    done: bool = False
    token_usage: Optional[Dict[str, int]] = None


class AgentRuntime:
    """Agent 运行时：持有 LLM 实例和工具列表，提供 invoke / stream 能力"""

    def __init__(self, agent_id: str, config: AgentConfig, llm: BaseChatModel, tools: Optional[List[BaseTool]] = None):
        self.agent_id = agent_id
        self.config = config
        self.llm = llm
        self.tools = tools or []
        self.usage_callback = LLMUsageCallback()

    def invoke(self, input_text: str, chat_history: Optional[List[BaseMessage]] = None) -> AgentResponse:
        """同步调用 Agent（组装 System + 历史 + 用户消息，调用 LLM）"""
        messages = [SystemMessage(content=self.config.system_prompt), HumanMessage(content=input_text)]
        if chat_history:
            messages = [SystemMessage(content=self.config.system_prompt)] + chat_history + [HumanMessage(content=input_text)]

        self.usage_callback.reset()

        llm_with_callbacks = self.llm
        if hasattr(self.llm, "callbacks"):
            llm_with_callbacks = self.llm.bind(callbacks=[self.usage_callback])

        if self.tools:
            llm_with_tools = llm_with_callbacks.bind_tools(self.tools)
            result = llm_with_tools.invoke(messages)
        else:
            result = llm_with_callbacks.invoke(messages)

        return AgentResponse(
            content=result.content if hasattr(result, "content") else str(result),
            agent_id=self.agent_id,
            token_usage={
                "prompt_tokens": self.usage_callback.prompt_tokens,
                "completion_tokens": self.usage_callback.completion_tokens,
                "total_tokens": self.usage_callback.total_tokens,
            },
        )

    async def stream(self, input_text: str, chat_history: Optional[List[BaseMessage]] = None) -> AsyncIterator[Chunk]:
        """流式调用 Agent（SSE 逐块输出）"""
        messages = [SystemMessage(content=self.config.system_prompt), HumanMessage(content=input_text)]
        if chat_history:
            messages = [SystemMessage(content=self.config.system_prompt)] + chat_history + [HumanMessage(content=input_text)]

        llm_with_callbacks = self.llm.bind(callbacks=[self.usage_callback])

        if self.tools:
            llm_with_tools = llm_with_callbacks.bind_tools(self.tools)
            async for chunk in llm_with_tools.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield Chunk(content=chunk.content)
                elif hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    yield Chunk(content=f"[Tool Call: {chunk.tool_calls}]")
        else:
            async for chunk in llm_with_callbacks.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield Chunk(content=chunk.content)

        yield Chunk(content="", done=True, token_usage={
            "prompt_tokens": self.usage_callback.prompt_tokens,
            "completion_tokens": self.usage_callback.completion_tokens,
            "total_tokens": self.usage_callback.total_tokens,
        })


class AgentManager:
    """Agent 管理器：从模型创建 Runtime 并缓存"""

    def __init__(self):
        self._cache: Dict[str, AgentRuntime] = {}

    def create_runtime(self, agent_model: AgentModel, tools: Optional[List[BaseTool]] = None) -> AgentRuntime:
        """从数据库 Agent 模型创建运行时实例"""
        system_prompt = agent_model.system_prompt
        if not system_prompt:
            system_prompt = get_default_system_prompt(agent_model.role)

        config = AgentConfig(
            name=agent_model.name,
            role=agent_model.role,
            llm_provider=agent_model.llm_provider,
            model_name=agent_model.model_name,
            temperature=agent_model.temperature,
            max_tokens=agent_model.max_tokens,
            system_prompt=system_prompt,
            enable_memory=agent_model.enable_memory,
            memory_window=agent_model.memory_window,
            memory_policy=agent_model.memory_policy,
        )

        llm = LLMFactory.create(
            provider=config.llm_provider,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        runtime = AgentRuntime(agent_id=agent_model.id, config=config, llm=llm, tools=tools)
        self._cache[agent_model.id] = runtime
        return runtime

    def get_runtime(self, agent_id: str) -> Optional[AgentRuntime]:
        return self._cache.get(agent_id)

    def remove_runtime(self, agent_id: str):
        self._cache.pop(agent_id, None)


agent_manager = AgentManager()
