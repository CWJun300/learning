"""关键词高亮。

安全要求（重点）：
**必须先对原文做 HTML 转义，再插入 <mark> 标签。**
如果顺序反了，笔记正文里写一段 <script> 或 <img onerror=...> 就能在前端执行，
这是很典型的存储型 XSS。
"""

import html
import re


def _plain(text: str, context: int) -> str:
    """没有可高亮词时的降级输出：转义 + 截断。"""
    fragment = text[: context * 2]
    result = html.escape(fragment, quote=False)
    if len(text) > len(fragment):
        result += "…"
    return result


def highlight(text: str, terms: list[str], context: int = 60) -> str:
    """返回带 <mark> 的 HTML 片段。

    :param text: 原始文本（可能是 Markdown 或含 HTML）
    :param terms: 要高亮的词条列表
    :param context: 命中位置前后各保留多少个字符
    """
    if not text:
        return ""

    terms = [t for t in (terms or []) if t]
    if not terms:
        return _plain(text, context)

    lowered = text.lower()
    positions = [lowered.find(term.lower()) for term in terms]
    positions = [pos for pos in positions if pos >= 0]
    if not positions:
        return _plain(text, context)

    first = min(positions)
    start = max(0, first - context)
    end = min(len(text), first + context)

    escaped = html.escape(text[start:end], quote=False)

    # 一次性替换：先转义词条，再合并成正则。单趟替换保证不会把
    # 后插入的 <mark> 标签本身再匹配一遍。
    needles = sorted({html.escape(term, quote=False) for term in terms}, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(needle) for needle in needles), re.IGNORECASE)
    result = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped)

    if start > 0:
        result = "…" + result
    if end < len(text):
        result += "…"
    return result
