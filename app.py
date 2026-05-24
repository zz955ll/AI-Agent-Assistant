"""
智能知识库问答系统 — 主入口
===============================
支持 TXT / PDF / MD / DOCX / CSV
基于语义检索（FAISS + 向量嵌入）+ 流式对话
"""

import os
import streamlit as st

from src import config
from src import document as doc_mgr
from src import embed
from src import ui

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="智能知识库问答",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

ui.apply_custom_css()
ui.render_header()
ui.render_settings_panel()


# ============================================================
# 初始化 session state
# ============================================================
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "vectorstore" not in st.session_state:
    st.session_state["vectorstore"] = None
if "chunks" not in st.session_state:
    st.session_state["chunks"] = None


# ============================================================
# 知识库构建逻辑
# ============================================================
def build_knowledge_base():
    """加载文档 → 切分 → 构建向量库"""
    if not config.has_api_key():
        st.error("⚠️ 请先配置 API Key")
        return False

    documents, errors = doc_mgr.load_directory("knowledge_base")
    if not documents:
        st.warning("📂 知识库为空，请先上传文档")
        return False

    # 显示错误但不中断
    for err in errors:
        st.warning(err)

    # 切分
    chunk_size = int(config.get_config("chunk_size", 500))
    chunk_overlap = int(config.get_config("chunk_overlap", 50))
    chunks = doc_mgr.split_documents(documents, chunk_size, chunk_overlap)

    # 构建向量库
    with st.spinner(f"🔄 正在构建索引 ({len(chunks)} 个片段)..."):
        vectorstore = embed.build_vectorstore(chunks)

    if vectorstore is None:
            st.error("构建向量库失败，请检查 API Key 是否正确")
            return False

    st.session_state["vectorstore"] = vectorstore
    st.session_state["chunks"] = chunks
    st.session_state["kb_dirty"] = False
    st.success(f"✅ 知识库构建完成！共 {len(chunks)} 个片段")

    # 保存到磁盘缓存
    try:
        embed.save_vectorstore(vectorstore, "knowledge_base/.vectorstore")
    except Exception:
        pass  # 非关键操作

    return True


def try_load_cached():
    """尝试从磁盘加载缓存的向量库"""
    if st.session_state.get("vectorstore") is not None:
        return  # 已经加载
    try:
        vs = embed.load_vectorstore("knowledge_base/.vectorstore")
        if vs is not None:
            st.session_state["vectorstore"] = vs
            # 重建 chunks 元数据（仅用于计数）
            files = doc_mgr.get_file_list("knowledge_base")
            if files:
                docs, _ = doc_mgr.load_directory("knowledge_base")
                if docs:
                    chunks = doc_mgr.split_documents(
                        docs,
                        int(config.get_config("chunk_size", 500)),
                        int(config.get_config("chunk_overlap", 50)),
                    )
                    st.session_state["chunks"] = chunks
    except Exception:
        pass


# ============================================================
# 主流程
# ============================================================

# 尝试加载缓存
try_load_cached()

# 响应构建请求
if st.session_state.get("rebuild"):
    st.session_state["rebuild"] = False
    build_knowledge_base()

# 响应知识库变更标记（上传/删除后自动触发）
if st.session_state.get("kb_dirty"):
    files = doc_mgr.get_file_list("knowledge_base")
    if not files:
        # 文档全删了，清空向量库
        st.session_state["vectorstore"] = None
        st.session_state["chunks"] = None
        st.session_state["kb_dirty"] = False
        if os.path.exists("knowledge_base/.vectorstore"):
            import shutil
            shutil.rmtree("knowledge_base/.vectorstore")
    st.session_state["kb_dirty"] = False
    st.rerun()

# 如果没有向量库但有文档，提示构建
if st.session_state.get("vectorstore") is None:
    files = doc_mgr.get_file_list("knowledge_base")
    if files:
        btn = st.button(f"📂 发现 {len(files)} 份文档，点击构建知识库", use_container_width=True)
        if btn:
            build_knowledge_base()

# 渲染对话区
ui.render_chat_area()
