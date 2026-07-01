"""Embedding 生成服务：将文本转换为向量嵌入，用于语义检索"""
from typing import List, Optional

from app.config import settings


class EmbeddingService:
    """Embedding 生成器 — 支持 OpenAI 兼容接口，可扩展其他供应商"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """延迟初始化 embedding 客户端"""
        if self._client is not None:
            return self._client

        api_key = settings.openai_api_key
        if not api_key:
            return None

        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            return self._client
        except ImportError:
            return None

    async def embed_query(self, text: str) -> Optional[List[float]]:
        """将查询文本转换为向量嵌入

        Args:
            text: 要嵌入的文本

        Returns:
            向量嵌入列表，失败时返回 None
        """
        client = self._get_client()
        if not client:
            return None

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception:
            return None

    async def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量将文本转换为向量嵌入

        Args:
            texts: 要嵌入的文本列表

        Returns:
            向量嵌入列表，每项失败时为 None
        """
        if not texts:
            return []

        client = self._get_client()
        if not client:
            return [None] * len(texts)

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            # 按 index 排序确保顺序正确
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception:
            return [None] * len(texts)


# 全局单例
embedding_service = EmbeddingService()
