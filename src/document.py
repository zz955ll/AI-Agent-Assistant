"""
文档加载模块 — 支持 TXT / PDF / MD / DOCX / CSV
完全不依赖 langchain_community document_loaders，避免触发 PyTorch
"""

import os
import csv
from typing import List, Tuple


def load_single_file(file_path: str) -> list:
    """根据文件扩展名加载单个文档"""
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in (".txt", ".md"):
            return _load_text(file_path)
        elif ext == ".pdf":
            return _load_pdf(file_path)
        elif ext == ".csv":
            return _load_csv(file_path)
        elif ext == ".docx":
            return _load_docx(file_path)
        return []
    except Exception as e:
        raise RuntimeError(f"加载失败 [{os.path.basename(file_path)}]: {e}")


def _load_text(file_path: str) -> list:
    """直接读取文本文件"""
    from langchain_core.documents import Document
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [Document(page_content=text, metadata={"source": os.path.basename(file_path)})]


def _load_pdf(file_path: str) -> list:
    """使用 pdfplumber 提取 PDF 文本（比 pypdf 快 3-10 倍）"""
    import pdfplumber
    from langchain_core.documents import Document
    docs = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                docs.append(Document(
                    page_content=text.strip(),
                    metadata={
                        "source": os.path.basename(file_path),
                        "page": i + 1,
                    }
                ))
    return docs


def _load_csv(file_path: str) -> list:
    """使用 csv 模块读取 CSV"""
    from langchain_core.documents import Document
    docs = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = "\n".join([f"{k}: {v}" for k, v in row.items() if v])
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": os.path.basename(file_path)},
                ))
    if not docs:
        # 无表头或空行，当纯文本读
        with open(file_path, "r", encoding="utf-8") as f2:
            text = f2.read()
        docs = [Document(page_content=text, metadata={"source": os.path.basename(file_path)})]
    return docs


def _load_docx(file_path: str) -> list:
    """使用 docx2txt 读取 Word 文档"""
    from langchain_core.documents import Document
    import docx2txt
    text = docx2txt.process(file_path)
    if text.strip():
        return [Document(page_content=text, metadata={"source": os.path.basename(file_path)})]
    return []


def load_directory(directory_path: str) -> Tuple[list, list]:
    """加载目录下所有支持的文档"""
    if not os.path.exists(directory_path):
        return [], []

    supported = {".txt", ".md", ".pdf", ".csv", ".docx"}
    all_docs = []
    errors = []

    for filename in sorted(os.listdir(directory_path)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported:
            continue

        file_path = os.path.join(directory_path, filename)
        try:
            docs = load_single_file(file_path)
            for d in docs:
                d.metadata["source"] = filename
                d.metadata["source_path"] = file_path
            all_docs.extend(docs)
        except Exception as e:
            errors.append(str(e))

    return all_docs, errors


def split_documents(documents, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
    """将文档切分为固定大小的块（纯 Python 实现，无外部依赖）"""
    from langchain_core.documents import Document
    result = []

    for doc in documents:
        text = doc.page_content
        separators = ["\n\n", "\n", "。", "！", "？", "；"]
        paragraphs = _split_text(text, separators)

        current = ""
        for para in paragraphs:
            if len(current) + len(para) <= chunk_size:
                current += para
            else:
                if current:
                    result.append(Document(
                        page_content=current.strip(),
                        metadata=dict(doc.metadata),
                    ))
                if len(para) > chunk_size:
                    for i in range(0, len(para), chunk_size - chunk_overlap):
                        segment = para[i:i + chunk_size]
                        if segment.strip():
                            result.append(Document(
                                page_content=segment.strip(),
                                metadata=dict(doc.metadata),
                            ))
                    current = ""
                else:
                    current = para

        if current:
            result.append(Document(
                page_content=current.strip(),
                metadata=dict(doc.metadata),
            ))

    return result


def _split_text(text: str, separators: list) -> list:
    """按多级分隔符递归切分文本"""
    if not separators:
        return [text]

    sep = separators[0]
    parts = text.split(sep) if sep else [text]
    rest = separators[1:]

    if not rest:
        # 保持分隔符
        result = []
        for i, p in enumerate(parts):
            if i < len(parts) - 1:
                p += sep
            result.append(p)
        return result

    result = []
    for p in parts:
        result.extend(_split_text(p, rest))
    return result


def get_file_list(directory_path: str) -> List[str]:
    """获取目录中所有文档的文件名"""
    if not os.path.exists(directory_path):
        return []
    supported = {".txt", ".md", ".pdf", ".csv", ".docx"}
    return sorted([
        f for f in os.listdir(directory_path)
        if os.path.splitext(f)[1].lower() in supported
    ])


def delete_file(directory_path: str, filename: str) -> bool:
    """删除指定文档"""
    file_path = os.path.join(directory_path, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
