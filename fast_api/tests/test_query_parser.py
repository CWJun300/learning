"""query_parser 行为约定（先于实现编写）。

支持的查询语法：
    普通词         -> should   （可选命中）
    +词            -> must     （全部必须命中）
    "完整短语"      -> phrases  （整体短语）
    #标签          -> tags
"""

from app.services.query_parser import parse_query


class TestBasicTerms:
    def test_plain_words_go_to_should(self):
        q = parse_query("苹果 香蕉")
        assert q.should == ["苹果", "香蕉"]
        assert q.must == []
        assert q.phrases == []
        assert q.tags == []

    def test_duplicated_words_are_deduplicated(self):
        q = parse_query("苹果 苹果")
        assert q.should == ["苹果"]


class TestSpecialSyntax:
    def test_quoted_phrase(self):
        q = parse_query('"知识管理"')
        assert q.phrases == ["知识管理"]
        assert q.should == []

    def test_plus_sign_means_must(self):
        q = parse_query("+fastapi 教程")
        assert q.must == ["fastapi"]
        assert q.should == ["教程"]

    def test_hash_means_tag(self):
        q = parse_query("#python 笔记")
        assert q.tags == ["python"]
        assert q.should == ["笔记"]

    def test_combined_syntax(self):
        q = parse_query('+fastapi "倒排索引" #python 检索')
        assert q.must == ["fastapi"]
        assert q.phrases == ["倒排索引"]
        assert q.tags == ["python"]
        assert q.should == ["检索"]


class TestBoundaryAndException:
    def test_empty_string(self):
        q = parse_query("")
        assert (q.must, q.should, q.phrases, q.tags) == ([], [], [], [])

    def test_whitespace_only(self):
        q = parse_query("   ")
        assert (q.must, q.should, q.phrases, q.tags) == ([], [], [], [])

    def test_unclosed_quote_does_not_crash(self):
        q = parse_query('"知识')
        assert "知识" in q.should

    def test_empty_tag_is_ignored(self):
        q = parse_query("#")
        assert q.tags == []

    def test_special_chars_only(self):
        q = parse_query("+ # \"\"")
        assert (q.must, q.should, q.phrases, q.tags) == ([], [], [], [])
