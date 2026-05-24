# 智能知识库问答系统 🤖

基于 RAG（检索增强生成）架构的智能问答系统，支持多格式文档上传、语义检索和多轮对话。

## 功能亮点

📄 **多格式支持** — 上传 TXT / PDF / Markdown / CSV / Word 文档，自动解析并建立索引

🔍 **语义检索** — 使用 FAISS 向量数据库 + DashScope Embeddings，理解问题语义而非关键词匹配

💬 **流式对话** — AI 回答逐字显示，交互体验流畅

🎯 **三种问答模式**
- **混合模式**（推荐）— 知识库相关用资料回答，无关问题自由回答
- **仅知识库** — 严格基于文档回答，不编造
- **自由问答** — 完全忽略知识库，纯 AI 对话

⚙️ **灵活配置**
- 多模型选择：qwen-turbo / qwen-plus / qwen-max
- 温度调节、最大 Token 数控制
- 简短回答模式
- 对话导出 Markdown / JSON

📁 **文档管理** — 上传、查看、删除文档，一键重建索引

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Streamlit |
| 向量数据库 | FAISS |
| 嵌入模型 | DashScope text-embedding-v3 |
| 大语言模型 | 通义千问 (qwen-plus/qwen-max) |
| 文档解析 | pdfplumber / python-docx / pypdf |

## 项目结构

```
.
├── app.py                  # 主入口 — streamlit run app.py
├── requirements.txt        # 依赖清单
├── .env.example            # 环境变量模板
├── knowledge_base/         # 文档存放目录
└── src/
    ├── config.py            # 配置管理
    ├── document.py          # 文档加载 & 切分
    ├── embed.py             # 向量嵌入 & 检索
    ├── llm.py               # 大模型调用（流式）
    └── ui.py                # Streamlit 界面
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

从 [阿里云百炼平台](https://bailian.console.aliyun.com/) 获取 DashScope API Key：

方式一（推荐）：在侧边栏直接输入
方式二：复制 `.env.example` 为 `.env`，填入 Key

### 3. 启动

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501 即可使用。

### 4. 使用流程

1. **直接聊天** — 不传文档也能直接问 AI
2. **上传文档** — 侧边栏上传 TXT/PDF/MD/CSV/DOCX
3. **构建索引** — 上传后点击「构建索引」，等待进度完成
4. **知识库问答** — 系统会根据文档内容回答您的问题

## 开发背景

本项目最初为单文件实现（基于 jieba 关键词检索），后重构为模块化 RAG 架构：
- 关键词检索 → FAISS 语义检索，准确率大幅提升
- 单文件 → 6 个模块，职责清晰，可扩展
- 非流式 → 流式输出，体验优化
- 仅 TXT/PDF → 支持 5 种文件格式

## 许可证

MIT
