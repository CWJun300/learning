"""recommend 行为约定（先于实现编写）：基于词条共现的相似笔记推荐。"""

import pytest

from app.services.index_store import InvertedIndex
from app.services.recommend import recommend_related


def build_index() -> InvertedIndex:
    idx = InvertedIndex()
    idx.add(1, "苹果 香蕉")
    idx.add(2, "苹果 香蕉 橙子")
    idx.add(3, "西瓜")
    return idx


class TestRecommend:
    def test_related_doc_is_returned(self):
        results = recommend_related(build_index(), doc_id=1)
        assert 2 in [doc_id for doc_id, _ in results]

    def test_unrelated_doc_is_excluded(self):
        results = recommend_related(build_index(), doc_id=1)
        assert 3 not in [doc_id for doc_id, _ in results]

    def test_self_is_excluded(self):
        results = recommend_related(build_index(), doc_id=1)
        assert 1 not in [doc_id for doc_id, _ in results]

    def test_identical_docs_score_one(self):
        idx = InvertedIndex()
        idx.add(1, "苹果 香蕉")
        idx.add(2, "苹果 香蕉")
        results = recommend_related(idx, doc_id=1)
        assert results[0][0] == 2
        assert results[0][1] == pytest.approx(1.0)

    def test_unknown_doc_returns_empty(self):
        assert recommend_related(build_index(), doc_id=999) == []

    def test_top_k_limits_results(self):
        idx = InvertedIndex()
        for i in range(2, 8):
            idx.add(i, "苹果 香蕉")
        idx.add(1, "苹果 香蕉")
        assert len(recommend_related(idx, doc_id=1, top_k=3)) == 3
