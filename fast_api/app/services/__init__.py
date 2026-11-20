"""索引内核：分词、倒排索引、排序、查询解析、高亮、推荐。

这些模块是纯 Python 逻辑，不依赖数据库，是 TDD 的主要对象。
"""

__all__ = [
    "tokenizer",
    "index_store",
    "ranker",
    "query_parser",
    "highlight",
    "recommend",
]
