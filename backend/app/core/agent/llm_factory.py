"""LLM 工厂：动态加载不同供应商的 ChatModel，支持回退策略"""
from typing import Any, Optional, Dict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain.callbacks.base import BaseCallbackHandler

from app.config import settings


LLM_PROVIDER_MAP: Dict[str, tuple] = {
    "openai": ("langchain_openai", "ChatOpenAI"),
    "deepseek": ("langchain_community.chat_models", "ChatDeepSeek"),
    "qwen": ("langchain_community.chat_models", "ChatTongyi"),
    "zhipu": ("langchain_community.chat_models", "ChatZhipuAI"),
}

API_KEY_MAP = {
    "openai": settings.openai_api_key,
    "deepseek": settings.deepseek_api_key,
    "qwen": settings.qwen_api_key,
    "zhipu": settings.zhipu_api_key,
}

DEFAULT_MODEL_MAP = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "zhipu": "glm-4-flash",
}


class LLMFactory:
    """根据供应商名称动态加载对应的 LangChain ChatModel"""

    @staticmethod
    def create(
        provider: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        callbacks: Optional[list] = None,
    ) -> BaseChatModel:
        if provider not in LLM_PROVIDER_MAP:
            raise ValueError(f"不支持的 LLM 供应商: {provider}。支持的供应商: {list(LLM_PROVIDER_MAP.keys())}")

        module_path, class_name = LLM_PROVIDER_MAP[provider]
        import importlib
        module = importlib.import_module(module_path)
        klass = getattr(module, class_name)

        kwargs: Dict[str, Any] = {
            "model": model_name or DEFAULT_MODEL_MAP[provider],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        api_key = API_KEY_MAP.get(provider)
        if api_key:
            kwargs["api_key"] = api_key

        if callbacks:
            kwargs["callbacks"] = callbacks

        return klass(**kwargs)

    @staticmethod
    def get_fallback_provider(primary_provider: str) -> str:
        """获取当前供应商的降级回退供应商"""
        fallback_chain = {
            "openai": "deepseek",
            "deepseek": "qwen",
            "qwen": "zhipu",
            "zhipu": "openai",
        }
        return fallback_chain.get(primary_provider, "openai")


class LLMUsageCallback(BaseCallbackHandler):
    """LangChain Callback：在 LLM 调用结束后收集 token 使用量"""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs):
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            self.prompt_tokens = usage.get("prompt_tokens", 0)
            self.completion_tokens = usage.get("completion_tokens", 0)
            self.total_tokens = usage.get("total_tokens", 0)

    def reset(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
