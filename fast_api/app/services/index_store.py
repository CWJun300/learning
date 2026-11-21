"""倒排索引：内存结构 + JSON 持久化。

数据结构（这是项目里"数据结构综合运用"的核心）：
    postings  : {词条: {文档ID: 词频}}   —— 倒排表
    doc_terms : {文档ID: {词条, ...}}    —— 正排表，用于快速删除/更新
    doc_len   : {文档ID: 词条总数}        —— BM25 要用文档长度

删除时靠 doc_terms 找到该文档出现过的所有词条，避免全表扫描。
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.services.tokenizer import Tokenizer


@dataclass
class Posting:
    """倒排表中的一条记录：某个文档对某个词条的贡献。"""

    doc_id: int
    tf: int = 1


class IndexLoadError(Exception):
    """索引文件缺失或损坏时抛出。"""


class InvertedIndex:
    def __init__(self, tokenizer: Tokenizer | None = None) -> None:
        self._tokenizer = tokenizer or Tokenizer()
        self._postings: dict[str, dict[int, int]] = {}
        self._doc_terms: dict[int, set[str]] = {}
        self._doc_len: dict[int, int] = {}

    # ---------- 写入 ----------
    def add(self, doc_id: int, text: str) -> None:
        """新增文档。若已存在，则先移除旧内容（等价于 update）。"""
        if doc_id in self._doc_terms:
            self.remove(doc_id)

        tokens = self._tokenizer.tokenize(text)
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1

        for term, tf in counts.items():
            self._postings.setdefault(term, {})[doc_id] = tf

        self._doc_terms[doc_id] = set(counts)
        self._doc_len[doc_id] = len(tokens)

    def remove(self, doc_id: int) -> None:
        terms = self._doc_terms.pop(doc_id, None)
        if not terms:
            return
        for term in terms:
            bucket = self._postings.get(term)
            if bucket is None:
                continue
            bucket.pop(doc_id, None)
            if not bucket:
                self._postings.pop(term, None)
        self._doc_len.pop(doc_id, None)

    def update(self, doc_id: int, text: str) -> None:
        self.add(doc_id, text)

    # ---------- 查询 ----------
    def postings(self, term: str) -> list[Posting]:
        bucket = self._postings.get(term, {})
        return [Posting(doc_id=doc_id, tf=tf) for doc_id, tf in sorted(bucket.items())]

    def doc_count(self) -> int:
        return len(self._doc_terms)

    def doc_length(self, doc_id: int) -> int:
        return self._doc_len.get(doc_id, 0)

    def doc_terms(self, doc_id: int) -> set[str]:
        return set(self._doc_terms.get(doc_id, ()))

    def doc_ids(self) -> list[int]:
        return list(self._doc_terms)

    def terms(self) -> set[str]:
        return set(self._postings)

    # 模糊匹配的最短查询长度：单字展开会命中太多噪音
    MIN_FUZZY_LEN = 2

    def expand_terms(self, term: str, min_len: int | None = None) -> list[str]:
        """把查询词展开成相关词条。

        - 精确命中：只返回它自己（保证精度）
        - 否则返回所有**包含**它的词条（搜 "sql" 能匹配 "mysql"）
        - 太短的查询不展开，避免噪音
        """
        if not term:
            return []
        if term in self._postings:
            return [term]
        limit = self.MIN_FUZZY_LEN if min_len is None else min_len
        if len(term) < limit:
            return []
        return [candidate for candidate in self._postings if term in candidate]

    def avg_doc_length(self) -> float:
        if not self._doc_len:
            return 0.0
        return sum(self._doc_len.values()) / len(self._doc_len)

    # ---------- 持久化 ----------
    def save(self, path: str | Path) -> None:
        payload = {
            "version": 1,
            "postings": {
                term: {str(doc_id): tf for doc_id, tf in bucket.items()}
                for term, bucket in self._postings.items()
            },
            "doc_len": {str(doc_id): length for doc_id, length in self._doc_len.items()},
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    @classmethod
    def load(cls, path: str | Path) -> "InvertedIndex":
        target = Path(path)
        try:
            raw = target.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise IndexLoadError(f"索引文件不存在: {target}") from exc
        except OSError as exc:
            raise IndexLoadError(f"索引文件无法读取: {target} ({exc})") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IndexLoadError(f"索引文件不是合法 JSON: {target}") from exc

        if not isinstance(payload, dict) or "postings" not in payload:
            raise IndexLoadError(f"索引文件结构不正确: {target}")

        index = cls()
        for term, bucket in payload.get("postings", {}).items():
            if not isinstance(bucket, dict):
                raise IndexLoadError(f"索引文件结构不正确: {target}")
            for doc_id, tf in bucket.items():
                index._postings.setdefault(term, {})[int(doc_id)] = int(tf)
        for doc_id, length in payload.get("doc_len", {}).items():
            index._doc_len[int(doc_id)] = int(length)

        # 正排表由倒排表反推，避免持久化冗余数据不一致
        for term, bucket in index._postings.items():
            for doc_id in bucket:
                index._doc_terms.setdefault(int(doc_id), set()).add(term)

        return index
