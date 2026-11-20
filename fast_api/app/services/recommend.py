"""相似笔记推荐：基于词条集合的 Jaccard 相似度。

Jaccard(A, B) = |A ∩ B| / |A ∪ B|

选择它而不是"向量 + 余弦"的原因：
- 不需要额外依赖和向量存储；
- 结果可解释（重合词越多越像），答辩时讲得清楚；
- 对几百到几千篇笔记的规模，性能完全够用。
"""

from app.services.index_store import InvertedIndex


def recommend_related(
    index: InvertedIndex, doc_id: int, top_k: int = 5
) -> list[tuple[int, float]]:
    """返回 [(相似文档ID, 相似度)]，按相似度降序、ID 升序。"""
    base = index.doc_terms(doc_id)
    if not base:
        return []

    scored: list[tuple[int, float]] = []
    for other in index.doc_ids():
        if other == doc_id:
            continue
        other_terms = index.doc_terms(other)
        if not other_terms:
            continue
        intersection = len(base & other_terms)
        if intersection == 0:
            continue
        union = len(base | other_terms)
        scored.append((other, intersection / union))

    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:top_k]
