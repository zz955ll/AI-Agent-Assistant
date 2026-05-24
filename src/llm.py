"""
大模型调用模块 — 支持流式 & 非流式输出
"""

from typing import Generator, List, Optional
from http import HTTPStatus


def _build_messages(query: str, contexts: Optional[List[str]] = None):
    """构建 prompt"""
    from . import config
    brief = config.get_config("brief_mode", False)
    style = "用一句话回答，20字以内，说重点，不要解释，不要问候，不要补充信息。" if brief else ""

    # 知识库模式：strict=仅知识库，hybrid=知识库+自由问答，off=自由问答
    kb_mode = config.get_config("kb_mode", "hybrid")

    if contexts and kb_mode != "off":
        context_text = "\n\n---\n\n".join(contexts)

        if kb_mode == "strict":
            system_prompt = (
                "你是一个专业的知识库问答助手。请严格基于参考资料回答问题。\n"
                "如果参考资料不足以回答问题，请如实说：资料中未找到相关信息。\n"
                f"回答要求：简洁、准确、有条理。{style}"
            )
        else:  # hybrid
            system_prompt = (
                "你是一个AI助手，配有知识库资料作为参考。\n"
                "如果问题与参考资料相关，请基于资料回答；如果问题与资料无关，直接用自己的知识回答。\n"
                f"回答要求：简洁、准确、有条理。{style}"
            )
        user_prompt = f"【参考资料】\n{context_text}\n\n【问题】\n{query}"
    else:
        system_prompt = (
            "你是一个有用的AI助手。请简洁准确地回答用户问题。"
            f"{style}"
        )
        user_prompt = query

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_answer(query: str, contexts: Optional[List[str]] = None) -> str:
    """非流式生成答案"""
    from . import config
    api_key = config.get_api_key()
    if not api_key:
        return "⚠️ 请先在侧边栏配置 API Key"

    messages = _build_messages(query, contexts)
    from dashscope import Generation

    try:
        response = Generation.call(
            model=config.get_config("llm_model", "qwen-plus"),
            messages=messages,
            api_key=api_key,
            max_tokens=config.get_config("max_tokens", 1024),
            temperature=config.get_config("temperature", 0.3),
            result_format="message",
        )
        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            return f"❌ API 调用失败: {response.message}"
    except Exception as e:
        return f"❌ 出错: {str(e)}"


def generate_answer_stream(
    query: str,
    contexts: Optional[List[str]] = None,
) -> Generator[str, None, None]:
    """流式生成答案，逐 chunk 产出文本"""
    from . import config
    api_key = config.get_api_key()
    if not api_key:
        yield "⚠️ 请先在侧边栏配置 API Key"
        return

    messages = _build_messages(query, contexts)
    from dashscope import Generation

    try:
        last_text = ""
        responses = Generation.call(
            model=config.get_config("llm_model", "qwen-plus"),
            messages=messages,
            api_key=api_key,
            max_tokens=config.get_config("max_tokens", 1024),
            temperature=config.get_config("temperature", 0.3),
            result_format="message",
            stream=True,
        )
        for response in responses:
            if response.status_code == HTTPStatus.OK:
                content = response.output.choices[0].message.content
                if content:
                    # DashScope 流式返回的是全文累积，需要差分去重
                    diff = content[len(last_text):] if last_text else content
                    if diff:
                        last_text = content
                        yield diff
            else:
                yield f"\n\n❌ API 错误: {response.message}"
                break
    except Exception as e:
        yield f"\n\n❌ 出错: {str(e)}"
