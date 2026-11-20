"""highlight 行为约定（先于实现编写）。

要求：
1. 命中词用 <mark> 包裹；
2. 只返回命中位置附近的片段（context 控制长度）；
3. **先转义再插标签**，防止笔记内容里的 HTML 被执行（XSS）。
"""

from app.services.highlight import highlight


class TestNormalHighlight:
    def test_term_is_wrapped_in_mark(self):
        out = highlight("我喜欢苹果", ["苹果"])
        assert "<mark>苹果</mark>" in out

    def test_multiple_occurrences_all_marked(self):
        out = highlight("苹果 和 苹果", ["苹果"])
        assert out.count("<mark>") == 2

    def test_multiple_terms_all_marked(self):
        out = highlight("苹果 香蕉", ["苹果", "香蕉"])
        assert "<mark>苹果</mark>" in out
        assert "<mark>香蕉</mark>" in out

    def test_case_insensitive_but_keeps_original_case(self):
        out = highlight("Python is great", ["python"])
        assert "<mark>Python</mark>" in out


class TestBoundary:
    def test_empty_text(self):
        assert highlight("", ["苹果"]) == ""

    def test_no_terms_returns_plain_text(self):
        out = highlight("苹果香蕉", [])
        assert "<mark>" not in out
        assert "苹果香蕉" in out

    def test_term_not_present_returns_plain_text(self):
        out = highlight("苹果香蕉", ["西瓜"])
        assert "<mark>" not in out
        assert "苹果香蕉" in out

    def test_long_text_is_truncated_to_snippet(self):
        text = "无关内容" * 100 + "苹果"
        out = highlight(text, ["苹果"], context=60)
        assert "<mark>苹果</mark>" in out
        assert len(out) < len(text)


class TestSecurity:
    def test_html_is_escaped(self):
        out = highlight("<script>alert(1)</script> 苹果", ["苹果"])
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_mark_inside_content_is_escaped(self):
        out = highlight("已有<mark>标签</mark>", ["标签"])
        assert out.count("<mark>") == 1
        assert "&lt;mark&gt;" in out

    def test_attribute_injection_is_escaped(self):
        out = highlight('<img src=x onerror="alert(1)"> 苹果', ["苹果"])
        assert "<img" not in out
