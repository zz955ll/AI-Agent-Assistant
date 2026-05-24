"""
UI 组件模块 — Streamlit 界面组件
"""

import os
import io
import json
import streamlit as st
from typing import List, Optional
from datetime import datetime

from . import config
from . import document as doc_mgr


# ============================================================
# 通用 UI 工具
# ============================================================

def apply_custom_css():
    """注入自定义 CSS 美化界面"""
    st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.9rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .status-ok { background: #dcfce7; color: #166534; }
    .status-warn { background: #fef3c7; color: #92400e; }
    .badge {
        display: inline-block;
        background: #e5e7eb;
        padding: 0.1rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        margin-right: 0.3rem;
    }
    footer { display: none !important; }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """渲染顶部标题区"""
    st.markdown('<p class="main-header">\U0001f916 智能知识库问答系统</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">'
        "支持 TXT / PDF / MD / DOCX / CSV ｜ 语义检索 ｜ 流式对话 ｜ 多模型"
        '</p>',
        unsafe_allow_html=True,
    )


# ============================================================
# 侧边栏 - 设置面板
# ============================================================

def render_settings_panel():
    """渲染侧边栏设置面板"""
    with st.sidebar:
        st.markdown("### ⚙️ 设置")

        # ----- API Key -----
        current_key = config.get_api_key()
        masked = current_key[:8] + "..." if len(current_key) > 12 else ""
        key_input = st.text_input(
            "DashScope API Key",
            type="password",
            value=current_key,
            placeholder="输入您的 API Key",
            help="从 https://bailian.console.aliyun.com/ 获取",
            label_visibility="collapsed",
        )
        if key_input != current_key:
            if key_input:
                st.session_state["runtime_api_key"] = key_input
                st.rerun()
            else:
                st.session_state.pop("runtime_api_key", None)

        if config.has_api_key():
            st.success("✅ API Key 已配置", icon="✅")
        else:
            st.warning("⚠️ 请配置 API Key", icon="⚠️")
            if st.button("📖 如何获取 Key?", use_container_width=True):
                st.session_state["show_key_guide"] = True

        if st.session_state.get("show_key_guide"):
            with st.expander("获取 API Key 步骤", expanded=True):
                st.markdown("""
1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 登录后点击右上角 → API-KEY 管理
3. 创建新 API Key
4. 复制粘贴到上方输入框
                """)
                if st.button("知道了", use_container_width=True):
                    st.session_state["show_key_guide"] = False
                    st.rerun()

        st.divider()

        # ----- 模型选择 -----
        current_model = config.get_config("llm_model", "qwen-plus")
        model_labels = list(config.SUPPORTED_LLM_MODELS.keys())
        model_descs = list(config.SUPPORTED_LLM_MODELS.values())
        try:
            idx = model_labels.index(current_model)
        except ValueError:
            idx = 1  # default to qwen-plus

        selected_model = st.selectbox(
            "🤖 选择模型",
            model_labels,
            index=idx,
            format_func=lambda x: f"{x} — {config.SUPPORTED_LLM_MODELS.get(x, '')}",
        )
        if selected_model != current_model:
            config.set_config("llm_model", selected_model)
            st.rerun()

        # ----- 生成参数 -----
        with st.expander("🎛️ 生成参数", expanded=False):
            current_temp = config.get_config("temperature", 0.3)
            temp = st.slider(
                "温度 (Temperature)", 0.0, 1.0,
                value=float(current_temp), step=0.1,
                help="越高回答越有创造性，越低越确定"
            )
            if temp != current_temp:
                config.set_config("temperature", temp)

            current_max = config.get_config("max_tokens", 1024)
            max_tokens = st.select_slider(
                "最大 Token 数", options=[256, 512, 1024, 2048, 4096],
                value=int(current_max),
            )
            if max_tokens != current_max:
                config.set_config("max_tokens", max_tokens)

            st.divider()

            brief = config.get_config("brief_mode", False)
            brief_toggle = st.checkbox("✂️ 简短回答模式", value=brief,
                                       help="让 AI 用一句话回答，不说废话")
            if brief_toggle != brief:
                config.set_config("brief_mode", brief_toggle)
                st.rerun()

            st.divider()

            # ----- 问答模式 -----
            current_kb_mode = config.get_config("kb_mode", "hybrid")
            kb_mode_options = ["hybrid", "strict", "off"]
            kb_mode_labels = {
                "hybrid": "🌐 混合模式（推荐）",
                "strict": "📚 仅知识库",
                "off": "💬 自由问答",
            }
            kb_mode = st.radio(
                "📡 问答模式",
                options=kb_mode_options,
                index=kb_mode_options.index(current_kb_mode),
                format_func=lambda x: kb_mode_labels[x],
                help="混合：知识库相关用资料，无关的自由回答 | 仅知识库：只基于文档回答 | 自由问答：完全不理文档",
            )
            if kb_mode != current_kb_mode:
                config.set_config("kb_mode", kb_mode)
                st.rerun()

        st.divider()

        # ----- 文档管理 -----
        render_document_manager()

        st.divider()

        # ----- 系统状态 & 操作 -----
        render_system_status()


def render_document_manager():
    """文档管理区域"""
    st.markdown("### 📁 知识库管理")

    # 上传文档
    uploaded_files = st.file_uploader(
        "上传文档",
        type=["txt", "pdf", "md", "csv", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="支持 TXT / PDF / Markdown / CSV / Word 格式",
    )

    if uploaded_files:
        saved = 0
        for f in uploaded_files:
            file_path = os.path.join("knowledge_base", f.name)
            with open(file_path, "wb") as fp:
                fp.write(f.getbuffer())
            saved += 1
        if saved > 0:
            st.success(f"✅ 已保存 {saved} 个文件到知识库")
            st.info("👉 点击下方「构建索引」使文档生效")
            st.session_state["kb_dirty"] = True
            st.rerun()

    # 文档列表 & 删除
    files = doc_mgr.get_file_list("knowledge_base")
    if files:
        st.markdown(f"**📄 共 {len(files)} 份文档**")
        for fname in files:
            col1, col2 = st.columns([5, 1])
            with col1:
                icon = {
                    ".txt": "📄", ".md": "📝", ".pdf": "📕",
                    ".csv": "📊", ".docx": "📃",
                }.get(os.path.splitext(fname)[1].lower(), "📄")
                st.markdown(f"{icon} {fname}")
            with col2:
                if st.button("✕", key=f"del_{fname}", help=f"删除 {fname}"):
                    doc_mgr.delete_file("knowledge_base", fname)
                    st.session_state["kb_dirty"] = True
                    st.rerun()
    else:
        st.info("暂无文档，请上传")

    # 重新构建知识库
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔨 构建索引", use_container_width=True, disabled=not files):
            st.session_state["rebuild"] = True
    with col2:
        if st.button("🗑️ 清空所有", use_container_width=True, disabled=not files):
            for fname in files:
                doc_mgr.delete_file("knowledge_base", fname)
            st.session_state["kb_dirty"] = True
            st.rerun()


def render_system_status():
    """系统状态区域"""
    st.markdown("### 📊 系统状态")

    api_ok = config.has_api_key()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**API 状态**")
        if api_ok:
            st.markdown('<span class="status-badge status-ok">已连接</span>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-warn">未配置</span>',
                        unsafe_allow_html=True)

    with col2:
        st.markdown("**检索方式**")
        st.markdown('<span class="status-badge status-ok">语义(向量)</span>',
                    unsafe_allow_html=True)

    kb = st.session_state.get("chunks")
    if kb:
        st.caption(f"知识库: {len(kb)} 个片段")
    else:
        st.caption("知识库: 空")

    # 清空对话
    if st.button("🔄 清空对话", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state.pop("conversation_exported", None)
        st.rerun()

    # 导出对话
    if st.session_state.get("messages"):
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("📥 导出 Markdown", use_container_width=True):
                md_content = _export_markdown(st.session_state["messages"])
                st.download_button(
                    "下载 .md",
                    data=md_content,
                    file_name=f"对话_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                )
        with export_col2:
            if st.button("📥 导出 JSON", use_container_width=True):
                json_content = _export_json(st.session_state["messages"])
                st.download_button(
                    "下载 .json",
                    data=json_content,
                    file_name=f"对话_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json",
                )


# ============================================================
# 主对话区
# ============================================================

def render_chat_area():
    """渲染主对话区域"""
    st.markdown("### 💬 对话")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # 显示对话历史
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander("📖 查看参考资料", expanded=False):
                    for i, src in enumerate(msg["sources"]):
                        st.markdown(f"**来源 {i+1}:** `{src.get('source', 'unknown')}`")
                        st.write(src.get("content", ""))
                        if i < len(msg["sources"]) - 1:
                            st.markdown("---")

    # 有文档未建索引时显示提示
    vec = st.session_state.get("vectorstore")
    if vec is None:
        files = doc_mgr.get_file_list("knowledge_base")
        if files:
            st.info("📚 有文档但未构建索引，回答将不基于知识库")

    # 输入框 — 始终可用
    if prompt := st.chat_input("请输入您的问题..."):
        _handle_query(prompt)


def _handle_query(query: str):
    """处理用户提问并生成回复"""
    from . import embed


    # 显示用户消息
    with st.chat_message("user"):
        st.write(query)

    vectorstore = st.session_state.get("vectorstore")

    with st.chat_message("assistant"):
        with st.status("正在分析...", expanded=True) as status:
            # Step 1: 检索
            contexts = []
            if vectorstore:
                try:
                    results = embed.search(query, vectorstore)
                    contexts = results
                    status.update(
                        label=f"📚 已检索到 {len(contexts)} 个相关片段",
                        state="complete",
                    )
                except Exception as e:
                    st.error(f"检索出错: {e}")

            # Step 2: 生成
            context_texts = [d.page_content for d in contexts] if contexts else None

            with st.spinner("🤔 思考中..."):
                # 流式输出
                from . import llm
                response_placeholder = st.empty()
                full_response = ""

                # 显示来源提示
                if contexts:
                    response_placeholder.info("📚 基于知识库回答")
                else:
                    response_placeholder.info("🌐 直接问答（无相关知识）")

                stream = llm.generate_answer_stream(query, context_texts)
                for chunk in stream:
                    full_response += chunk

                # 清掉提示信息，显示完整回答
                response_placeholder.empty()
                response_placeholder.markdown(full_response)

        # 展开参考资料
        if contexts:
            with st.expander("📖 查看参考资料", expanded=False):
                for i, doc in enumerate(contexts):
                    source = doc.metadata.get("source", "unknown")
                    st.markdown(f"**来源 {i+1}:** `{source}`")
                    st.write(doc.page_content)
                    st.markdown("---")

    # 保存到历史（不 rerun，避免重复渲染）
    st.session_state["messages"].append({
        "role": "user",
        "content": query,
    })
    st.session_state["messages"].append({
        "role": "assistant",
        "content": full_response,
        "sources": [
            {"source": d.metadata.get("source", "unknown"), "content": d.page_content}
            for d in (contexts or [])
        ],
    })


# ============================================================
# 导出工具
# ============================================================

def _export_markdown(messages: list) -> str:
    """导出为 Markdown"""
    lines = ["# 对话记录\n", f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n", "---\n"]
    for msg in messages:
        role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
        lines.append(f"### {role}\n")
        lines.append(f"{msg['content']}\n")
        if msg.get("sources"):
            lines.append("> 参考来源:\n")
            for src in msg["sources"]:
                lines.append(f"> - `{src['source']}`\n")
        lines.append("\n---\n")
    return "\n".join(lines)


def _export_json(messages: list) -> str:
    """导出为 JSON"""
    export = []
    for msg in messages:
        entry = {"role": msg["role"], "content": msg["content"]}
        if msg.get("sources"):
            entry["sources"] = msg["sources"]
        export.append(entry)
    return json.dumps(export, ensure_ascii=False, indent=2)
