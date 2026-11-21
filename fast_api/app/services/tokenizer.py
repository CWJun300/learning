"""分词器：中文用 jieba，英文/数字按 ASCII 连续串切分。

设计要点（也是测试驱动得出的结论）：
- 全小写，避免 "Python" 与 "python" 被当成两个词；
- 英文与数字单独抽出来，避免 jieba 把 "Python3.13" 拆成奇怪的东西；
- 中文单字丢弃，因为单字几乎没有区分度；
- 停用词过滤。
"""

import re

import jieba

# 英文单词（允许中间有下划线、+# 等编程常见符号）或者数字（允许小数点）
_ASCII_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_+#]*|[0-9]+(?:\.[0-9]+)?")
_CJK = re.compile(r"[\u4e00-\u9fff]")

DEFAULT_STOPWORDS: set[str] = {
    "的", "了", "和", "是", "在", "我", "有", "就", "不", "人", "都", "一",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看",
    "好", "自己", "这", "那", "与", "及", "或", "等", "被", "把", "对", "从",
    "为", "一个", "什么", "可以", "如果", "因为", "所以", "但是",
}


class Tokenizer:
    """中文 + 英文混合分词器。"""

    def __init__(self, stopwords: set[str] | None = None) -> None:
        # 传 None 用内置停用词表；传空集合表示不过滤停用词
        self._stopwords: set[str] = set(DEFAULT_STOPWORDS) if stopwords is None else set(stopwords)

    @property
    def stopwords(self) -> set[str]:
        return set(self._stopwords)

    def tokenize(self, text: str) -> list[str]:
        if text is None:
            raise TypeError("text 不能为 None")
        if not text:
            return []

        lowered = str(text).lower()
        tokens: list[str] = []

        # 1) 英文与数字
        for match in _ASCII_WORD.finditer(lowered):
            tokens.append(match.group())

        # 2) 中文：先把英文数字抹掉，避免 jieba 二次切分
        cjk_text = _ASCII_WORD.sub(" ", lowered)
        for piece in jieba.lcut(cjk_text):
            piece = piece.strip()
            if not piece or not _CJK.search(piece):
                continue
            # 注意：这里**不按字数丢弃**。jieba 会把「后端」「倒排」这类词
            # 切成单字，一旦丢掉就彻底检索不到了，噪音交给停用词表处理。
            tokens.append(piece)

        # 3) 停用词
        return [t for t in tokens if t and t not in self._stopwords]
