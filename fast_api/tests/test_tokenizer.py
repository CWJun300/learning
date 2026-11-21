"""Tokenizer 行为约定（先于实现编写）。

规则：
1. 全部转小写；
2. 英文/数字按 ASCII 连续串切分，保留 "python3"、"13" 这样的整体；
3. 中文用 jieba 切分，丢弃单字（噪音）；
4. 丢弃纯标点、空白、停用词。
"""

import pytest

from app.services.tokenizer import Tokenizer


class TestNormalInput:
    def test_chinese_words_are_split(self):
        assert Tokenizer().tokenize("苹果 香蕉 橙子") == ["苹果", "香蕉", "橙子"]

    def test_english_is_lowercased(self):
        assert Tokenizer().tokenize("Python FastAPI") == ["python", "fastapi"]

    def test_mixed_chinese_and_english(self):
        toks = Tokenizer().tokenize("用 FastAPI 写接口")
        assert "fastapi" in toks
        assert "接口" in toks

    def test_version_number_is_split_into_word_and_number(self):
        assert Tokenizer().tokenize("Python3.13") == ["python3", "13"]


class TestBoundaryInput:
    def test_empty_string_returns_empty_list(self):
        assert Tokenizer().tokenize("") == []

    def test_only_punctuation_returns_empty_list(self):
        assert Tokenizer().tokenize("，。！？；：") == []

    def test_stopword_single_char_is_dropped(self):
        assert Tokenizer().tokenize("的") == []

    def test_meaningful_single_char_is_kept(self):
        # 不能因为"只有一个字"就丢掉：jieba 会把「后端」切成「后」「端」，
        # 一丢就导致这类词彻底搜不到
        assert Tokenizer().tokenize("写") == ["写"]

    def test_stopword_is_filtered(self):
        assert Tokenizer().tokenize("的 苹果") == ["苹果"]

    def test_custom_stopwords(self):
        tk = Tokenizer(stopwords={"苹果"})
        assert tk.tokenize("苹果 香蕉") == ["香蕉"]

    def test_long_text_does_not_crash(self):
        toks = Tokenizer().tokenize("苹果" * 5000)
        assert len(toks) > 0


class TestExceptionInput:
    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            Tokenizer().tokenize(None)
