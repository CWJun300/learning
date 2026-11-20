"""BM25 相关度排序。

公式（对每个查询词累加）：

    idf = ln(1 + (N - df + 0.5) / (df + 0.5))
    score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

其中 N 是文档总数，df 是包含该词的文档数，tf 是该词在文档中的词频，
dl 是文档长度，avgdl 是平均文档长度。
k1 控制词频饱和速度，b 控制文档长度归一化强度。
"""

import math

from app.services.index_store import InvertedIndex


class BM25Ranker:
    def __init__(self, index: InvertedIndex, k1: float = 1.5, b: float = 0.75) -> None:
        self.index = index
        self.k1 = k1
        self.b = b

    def score(self, doc_id: int, query_terms: list[str]) -> float:
        total_docs = self.index.doc_count()
        if total_docs == 0 or not query_terms:
            return 0.0

        doc_len = self.index.doc_length(doc_id)
        avg_len = self.index.avg_doc_length() or 1.0

        total = 0.0
        for term in query_terms:
            posting = {p.doc_id: p.tf for p in self.index.postings(term)}
            tf = posting.get(doc_id, 0)
            if not tf:
                continue
            df = len(posting)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_len)
            total += idf * (tf * (self.k1 + 1)) / denominator
        return total

    def search(self, query_terms: list[str], top_k: int = 20) -> list[tuple[int, float]]:
        if not query_terms or self.index.doc_count() == 0:
            return []

        candidates: set[int] = set()
        for term in query_terms:
            candidates.update(p.doc_id for p in self.index.postings(term))

        scored = [(doc_id, self.score(doc_id, query_terms)) for doc_id in candidates]
        scored = [item for item in scored if item[1] > 0]
        # 得分降序；得分相同时按 doc_id 升序，保证结果稳定可测
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]
