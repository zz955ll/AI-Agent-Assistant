"""
向量嵌入 & 检索模块 — 使用 DashScope Embedding + FAISS
"""

import os
from typing import Optional


def _get_embeddings():
    from . import config
    api_key = config.get_api_key()
    if not api_key:
        return None
    from langchain_community.embeddings import DashScopeEmbeddings
    return DashScopeEmbeddings(
        model=config.get_config("embedding_model", "text-embedding-v3"),
        dashscope_api_key=api_key,
    )


def build_vectorstore(chunks):
    """构建 FAISS 向量库"""
    embeddings = _get_embeddings()
    if embeddings is None:
        return None

    from langchain_community.vectorstores import FAISS
    try:
        # 直接一次性构建（不进行分批 add，避免 API 兼容问题）
        return FAISS.from_documents(chunks, embeddings)
    except Exception as e:
        raise RuntimeError(f"构建向量库失败: {e}")


def search(query: str, vectorstore, k: Optional[int] = None):
    """语义检索，返回最相关的 k 个文档块"""
    from . import config
    if k is None:
        k = config.get_config("retrieve_k", 4)
    try:
        return vectorstore.similarity_search(query, k=k)
    except Exception as e:
        raise RuntimeError(f"检索失败: {e}")


def save_vectorstore(vectorstore, path: str):
    """持久化保存向量库到磁盘"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    vectorstore.save_local(path)


def load_vectorstore(path: str):
    """从磁盘加载向量库"""
    if not os.path.exists(path):
        return None
    embeddings = _get_embeddings()
    if embeddings is None:
        return None
    from langchain_community.vectorstores import FAISS
    try:
        return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    except Exception:
        return None
