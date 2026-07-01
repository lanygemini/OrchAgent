"""Agent 管理器：创建 / 缓存 / 获取 AgentRuntime，驱动 Agent 的 invoke / stream（含 ReAct 工具调用循环）"""
import asyncio
from typing import Optional, AsyncIterator, Dict, Any, List
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.agent.llm_factory import LLMFactory, LLMUsageCallback
from app.core.prompts import get_default_system_prompt
from app.models.agent import Agent as AgentModel

# ReAct 循环最大迭代次数，防止无限工具调用
MAX_REACT_ITERATIONS = 10


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
        """同步调用 Agent（ReAct 循环：LLM → tool_calls → 执行工具 → 回灌 → 再调用 LLM，直到无 tool_calls）"""
        messages = [SystemMessage(content=self.config.system_prompt)]
        if chat_history:
            messages = messages + list(chat_history)
        messages.append(HumanMessage(content=input_text))

        self.usage_callback.reset()
        callbacks = [self.usage_callback]
        invoke_kwargs: Dict[str, Any] = {}
        if hasattr(self.llm, "callbacks"):
            invoke_kwargs["config"] = {"callbacks": callbacks}

        # 无工具时直接调用 LLM
        if not self.tools:
            result = self.llm.invoke(messages, **invoke_kwargs)
            return AgentResponse(
                content=result.content if hasattr(result, "content") else str(result),
                agent_id=self.agent_id,
                token_usage={
                    "prompt_tokens": self.usage_callback.prompt_tokens,
                    "completion_tokens": self.usage_callback.completion_tokens,
                    "total_tokens": self.usage_callback.total_tokens,
                },
            )

        # ReAct 循环：LLM → tool_calls → 执行工具 → 回灌 → 再调用 LLM
        llm_with_tools = self.llm.bind_tools(self.tools)
        tool_map = {t.name: t for t in self.tools}

        for _ in range(MAX_REACT_ITERATIONS):
            result = llm_with_tools.invoke(messages, **invoke_kwargs)

            # 无 tool_calls，循环结束
            if not getattr(result, "tool_calls", None):
                break

            # 将 AI 的工具调用消息加入历史
            messages.append(result)

            # 逐个执行工具并回灌 ToolMessage
            for tc in result.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool = tool_map.get(tool_name)
                if tool:
                    try:
                        tool_result = tool.invoke(tool_args)
                        messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc.get("id", "")))
                    except Exception as e:
                        messages.append(ToolMessage(content=f"工具执行出错: {e}", tool_call_id=tc.get("id", "")))
                else:
                    messages.append(ToolMessage(content=f"工具 {tool_name} 未找到", tool_call_id=tc.get("id", "")))
        else:
            # 达到最大迭代次数，追加提示让 LLM 总结
            messages.append(HumanMessage(content="已达到最大工具调用次数，请基于已有信息给出最终回答。"))
            result = llm_with_tools.invoke(messages, **invoke_kwargs)

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
        """流式调用 Agent（SSE 逐块输出，支持 ReAct 工具调用循环）"""
        messages = [SystemMessage(content=self.config.system_prompt)]
        if chat_history:
            messages = messages + list(chat_history)
        messages.append(HumanMessage(content=input_text))

        self.usage_callback.reset()
        llm_with_callbacks = self.llm.bind(callbacks=[self.usage_callback])

        # 无工具时直接流式输出
        if not self.tools:
            async for chunk in llm_with_callbacks.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield Chunk(content=chunk.content)
            yield Chunk(content="", done=True, token_usage={
                "prompt_tokens": self.usage_callback.prompt_tokens,
                "completion_tokens": self.usage_callback.completion_tokens,
                "total_tokens": self.usage_callback.total_tokens,
            })
            return

        # ReAct 循环流式输出
        llm_with_tools = llm_with_callbacks.bind_tools(self.tools)
        tool_map = {t.name: t for t in self.tools}

        for iteration in range(MAX_REACT_ITERATIONS):
            has_tool_calls = False
            accumulated_content = ""
            tool_calls_accum: List[Dict[str, Any]] = []

            # 流式接收 LLM 响应
            async for chunk in llm_with_tools.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    accumulated_content += chunk.content
                    yield Chunk(content=chunk.content)
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    has_tool_calls = True
                    # 累积 tool_calls（流式中可能分多块到达）
                    for tc in chunk.tool_calls:
                        if tc.get("name"):
                            tool_calls_accum.append(tc)
                            yield Chunk(content=f"\n🔧 调用工具: {tc['name']}({tc.get('args', {})})\n")

            # 无工具调用，循环结束
            if not has_tool_calls:
                break

            # 将 AI 消息和工具结果加入历史
            ai_msg = AIMessage(content=accumulated_content, tool_calls=tool_calls_accum)
            messages.append(ai_msg)

            # 逐个执行工具并回灌
            for tc in tool_calls_accum:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool = tool_map.get(tool_name)
                if tool:
                    try:
                        tool_result = await tool.ainvoke(tool_args)
                        result_str = str(tool_result)
                        yield Chunk(content=f"📋 工具结果: {result_str[:200]}\n")
                        messages.append(ToolMessage(content=result_str, tool_call_id=tc.get("id", "")))
                    except Exception as e:
                        err_msg = f"工具执行出错: {e}"
                        yield Chunk(content=f"❌ {err_msg}\n")
                        messages.append(ToolMessage(content=err_msg, tool_call_id=tc.get("id", "")))
                else:
                    not_found = f"工具 {tool_name} 未找到"
                    yield Chunk(content=f"❌ {not_found}\n")
                    messages.append(ToolMessage(content=not_found, tool_call_id=tc.get("id", "")))
        else:
            # 达到最大迭代次数
            messages.append(HumanMessage(content="已达到最大工具调用次数，请基于已有信息给出最终回答。"))
            async for chunk in llm_with_tools.astream(messages):
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
