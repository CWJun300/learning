class Tokenizer:
    """中文 + 英文混合分词器。"""

    def __init__(self, stopwords: set[str] | None = None) -> None:
        raise NotImplementedError("待实现：见 tests/test_tokenizer.py")

    def tokenize(self, text: str) -> list[str]: ...
