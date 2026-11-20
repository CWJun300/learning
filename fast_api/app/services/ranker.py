class BM25Ranker:
    """基于倒排索引的 BM25 相关度打分。"""

    def __init__(self, index, k1: float = 1.5, b: float = 0.75) -> None:
        raise NotImplementedError("待实现：见 tests/test_ranker.py")

    def score(self, doc_id: int, query_terms: list[str]) -> float: ...
    def search(self, query_terms: list[str], top_k: int = 20) -> list[tuple[int, float]]: ...
