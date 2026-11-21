"""BM25Ranker 行为约定（先于实现编写）。"""

from app.services.index_store import InvertedIndex
from app.services.ranker import BM25Ranker


def build_ranker() -> BM25Ranker:
    """构造一个可预测的小索引：

    doc 1: 苹果 香蕉
    doc 2: 苹果 苹果 橙子
    doc 3: 西瓜
    """
    idx = InvertedIndex()
    idx.add(1, "苹果 香蕉")
    idx.add(2, "苹果 苹果 橙子")
    idx.add(3, "西瓜")
    return BM25Ranker(idx)


class TestScore:
    def test_hit_scores_positive(self):
        ranker = build_ranker()
        assert ranker.score(1, ["苹果"]) > 0

    def test_miss_scores_zero(self):
        assert build_ranker().score(3, ["苹果"]) == 0.0

    def test_short_doc_scores_higher_on_same_tf(self):
        """b 参数生效：文档越短，同样词频得分越高。"""
        idx = InvertedIndex()
        idx.add(1, "苹果")
        idx.add(2, "苹果 香蕉 橙子 西瓜 葡萄")
        ranker = BM25Ranker(idx)
        assert ranker.score(1, ["苹果"]) > ranker.score(2, ["苹果"])

    def test_params_are_configurable(self):
        ranker = BM25Ranker(InvertedIndex(), k1=2.0, b=0.5)
        assert ranker.k1 == 2.0
        assert ranker.b == 0.5


class TestSearch:
    def test_single_term_hit(self):
        results = build_ranker().search(["苹果"])
        assert {doc_id for doc_id, _ in results} == {1, 2}

    def test_no_hit_returns_empty_list(self):
        assert build_ranker().search(["不存在的词"]) == []

    def test_multiple_terms_full_match_ranks_first(self):
        idx = InvertedIndex()
        idx.add(1, "苹果")
        idx.add(2, "苹果 香蕉")
        results = BM25Ranker(idx).search(["苹果", "香蕉"])
        assert results[0][0] == 2

    def test_top_k_limits_results(self):
        results = build_ranker().search(["苹果"], top_k=1)
        assert len(results) == 1

    def test_tie_broken_by_doc_id_ascending(self):
        idx = InvertedIndex()
        idx.add(5, "苹果")
        idx.add(2, "苹果")
        results = BM25Ranker(idx).search(["苹果"])
        assert [doc_id for doc_id, _ in results] == [2, 5]

    def test_empty_query_returns_empty_list(self):
        assert build_ranker().search([]) == []

    def test_empty_index_returns_empty_list(self):
        assert BM25Ranker(InvertedIndex()).search(["苹果"]) == []


class TestFuzzyFallback:
    """精确词条搜不到时，退化为「包含关系」匹配（sql -> mysql）。"""

    def test_partial_word_matches_when_no_exact(self):
        idx = InvertedIndex()
        idx.add(1, "mysql 连接池")
        results = BM25Ranker(idx).search(["sql"])
        assert [doc_id for doc_id, _ in results] == [1]

    def test_exact_match_takes_priority(self):
        idx = InvertedIndex()
        idx.add(1, "mysql")
        idx.add(2, "sql")
        results = BM25Ranker(idx).search(["sql"])
        assert [doc_id for doc_id, _ in results] == [2]

    def test_single_char_query_does_not_expand(self):
        idx = InvertedIndex()
        idx.add(1, "mysql")
        assert BM25Ranker(idx).search(["s"]) == []

    def test_short_query_does_not_expand(self):
        idx = InvertedIndex()
        idx.add(1, "mysql")
        assert BM25Ranker(idx).search(["q"]) == []

    def test_no_candidate_returns_empty(self):
        idx = InvertedIndex()
        idx.add(1, "mysql")
        assert BM25Ranker(idx).search(["zzzz"]) == []

    def test_expand_terms_helper(self):
        idx = InvertedIndex()
        idx.add(1, "mysql postgresql sqlite")
        assert sorted(idx.expand_terms("sql")) == ["mysql", "postgresql", "sqlite"]
        assert idx.expand_terms("sqlite") == ["sqlite"]
