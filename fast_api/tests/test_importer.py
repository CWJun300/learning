"""批量导入的解析逻辑（纯函数，便于单测）。"""

import pytest

from app.services.importer import parse_any, parse_json, parse_markdown


class TestMarkdown:
    def test_title_from_h1_heading(self):
        note = parse_markdown("随便.md", "# 我的标题\n\n正文内容")
        assert note.title == "我的标题"
        assert note.content == "正文内容"

    def test_title_falls_back_to_filename(self):
        note = parse_markdown("数据库笔记.md", "没有一级标题的正文")
        assert note.title == "数据库笔记"
        assert note.content == "没有一级标题的正文"

    def test_front_matter_title_and_tags(self):
        text = "---\ntitle: 前端笔记\ntags: Vue, 前端\n---\n正文"
        note = parse_markdown("x.md", text)
        assert note.title == "前端笔记"
        assert note.tags == ["Vue", "前端"]
        assert note.content == "正文"

    def test_front_matter_bracket_tags(self):
        text = "---\ntags: [a, b]\n---\n正文"
        assert parse_markdown("x.md", text).tags == ["a", "b"]

    def test_front_matter_is_removed_from_content(self):
        text = "---\ntags: 测试\n---\n\n# 标题\n正文"
        note = parse_markdown("x.md", text)
        assert "---" not in note.content
        assert "tags" not in note.content
        assert note.title == "标题"

    def test_empty_content(self):
        note = parse_markdown("空.md", "")
        assert note.title == "空"
        assert note.content == ""

    def test_heading_not_duplicated_in_content(self):
        note = parse_markdown("x.md", "# 标题\n正文")
        assert "# 标题" not in note.content


class TestJson:
    def test_list_of_notes(self):
        text = '[{"title": "A", "content": "aaa", "tags": ["x"]}]'
        notes = parse_json("a.json", text)
        assert len(notes) == 1
        assert notes[0].title == "A"
        assert notes[0].tags == ["x"]

    def test_wrapped_in_notes_key(self):
        text = '{"notes": [{"title": "B", "content": "bbb"}]}'
        assert parse_json("b.json", text)[0].title == "B"

    def test_single_object(self):
        text = '{"title": "C", "content": "ccc"}'
        assert parse_json("c.json", text)[0].title == "C"

    def test_missing_title_falls_back_to_filename(self):
        text = '[{"content": "只有正文"}]'
        assert parse_json("我的文件.json", text)[0].title == "我的文件"

    def test_tags_as_string(self):
        text = '[{"title": "D", "content": "d", "tags": "a, b"}]'
        assert parse_json("d.json", text)[0].tags == ["a", "b"]

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            parse_json("bad.json", "{ not json")


class TestParseAny:
    def test_txt_is_treated_as_markdown(self):
        note = parse_any("笔记.txt", "# 标题\n内容")[0]
        assert note.title == "标题"

    def test_md_dispatch(self):
        assert parse_any("a.md", "# X\nY")[0].title == "X"

    def test_unknown_extension_still_parsed_as_text(self):
        assert parse_any("a.log", "纯文本")[0].title == "a"

    def test_json_returns_multiple(self):
        notes = parse_any("m.json", '[{"title": "1"}, {"title": "2"}]')
        assert len(notes) == 2
