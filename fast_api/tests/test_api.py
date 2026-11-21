"""接口测试（需要 MySQL 的 kb_test 库）。

约定：涉及"词条精确命中"的用例统一用 ASCII 词（如 alpha、beta），
因为中文短词会被分词器按规则丢弃，导致断言不稳定。
"""

import pytest

pytestmark = pytest.mark.db


def create_note(client, title, content="", tags=None):
    return client.post(
        "/api/notes",
        json={"title": title, "content": content, "tags": tags or []},
    )


class TestHealth:
    def test_health_reports_db_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"

    def test_index_starts_empty_in_tests(self, client):
        assert client.get("/api/health").json()["index_docs"] == 0


class TestCreate:
    def test_create_returns_201_with_tags(self, client):
        response = create_note(client, "倒排索引笔记", "倒排索引是检索核心", ["检索"])
        assert response.status_code == 201
        body = response.json()
        assert body["id"] > 0
        assert body["title"] == "倒排索引笔记"
        assert [tag["name"] for tag in body["tags"]] == ["检索"]

    def test_create_rejects_empty_title(self, client):
        assert client.post("/api/notes", json={"title": "", "content": "x"}).status_code == 422

    def test_create_dedupes_tags(self, client):
        body = create_note(client, "去重", tags=["python", "python"]).json()
        assert [tag["name"] for tag in body["tags"]] == ["python"]


class TestRead:
    def test_get_detail(self, client):
        note_id = create_note(client, "标题甲", "正文").json()["id"]
        body = client.get(f"/api/notes/{note_id}").json()
        assert body["title"] == "标题甲"
        assert body["content"] == "正文"

    def test_get_missing_returns_unified_error(self, client):
        response = client.get("/api/notes/999999")
        assert response.status_code == 404
        assert set(response.json()) == {"code", "message"}


class TestList:
    def test_pagination(self, client):
        for index in range(3):
            create_note(client, f"笔记{index}")
        body = client.get("/api/notes?page=1&size=2").json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["page"] == 1 and body["size"] == 2

    def test_filter_by_tag(self, client):
        create_note(client, "带标签的", tags=["python"])
        create_note(client, "不带标签的")
        body = client.get("/api/notes?tag=python").json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "带标签的"

    def test_invalid_page_size_rejected(self, client):
        assert client.get("/api/notes?size=1000").status_code == 422


class TestUpdateAndDelete:
    def test_update_title(self, client):
        note_id = create_note(client, "旧标题", "旧内容").json()["id"]
        body = client.put(f"/api/notes/{note_id}", json={"title": "新标题"}).json()
        assert body["title"] == "新标题"
        assert body["content"] == "旧内容"  # 未传的字段保持不变

    def test_update_unknown_returns_404(self, client):
        assert client.put("/api/notes/999999", json={"title": "x"}).status_code == 404

    def test_delete_then_get_404(self, client):
        note_id = create_note(client, "待删除").json()["id"]
        assert client.delete(f"/api/notes/{note_id}").status_code == 204
        assert client.get(f"/api/notes/{note_id}").status_code == 404


class TestSearch:
    def test_hit_and_highlight(self, client):
        create_note(client, "机器学习入门", "这是一篇关于机器学习的文章")
        body = client.get("/api/search", params={"q": "机器学习"}).json()
        assert body["total"] >= 1
        assert "<mark>" in body["items"][0]["snippet"]

    def test_no_result(self, client):
        assert client.get("/api/search", params={"q": "zzzznotexist"}).json()["total"] == 0

    def test_query_is_required(self, client):
        assert client.get("/api/search").status_code == 422

    def test_update_indexes_new_content(self, client):
        """改完内容后，新词要能搜到、旧词要搜不到——验证索引与数据库同步。"""
        note_id = create_note(client, "标题固定", "oldword 内容").json()["id"]
        client.put(f"/api/notes/{note_id}", json={"content": "newword 内容"})
        assert client.get("/api/search", params={"q": "newword"}).json()["total"] >= 1
        assert client.get("/api/search", params={"q": "oldword"}).json()["total"] == 0

    def test_delete_removes_from_index(self, client):
        note_id = create_note(client, "zebraword 独有").json()["id"]
        assert client.get("/api/search", params={"q": "zebraword"}).json()["total"] == 1
        client.delete(f"/api/notes/{note_id}")
        assert client.get("/api/search", params={"q": "zebraword"}).json()["total"] == 0

    def test_must_operator_filters(self, client):
        create_note(client, "alpha 笔记", "alpha only")
        create_note(client, "beta 笔记", "beta only")
        body = client.get("/api/search", params={"q": "+beta"}).json()
        titles = [item["title"] for item in body["items"]]
        assert "beta 笔记" in titles
        assert "alpha 笔记" not in titles

    def test_tag_filter_in_query(self, client):
        create_note(client, "带标签", "gamma 内容", tags=["fastapi"])
        create_note(client, "无标签", "gamma 内容")
        body = client.get("/api/search", params={"q": "gamma #fastapi"}).json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "带标签"

    def test_snippet_escapes_html(self, client):
        create_note(client, "安全测试", "<script>alert(1)</script> 苹果")
        body = client.get("/api/search", params={"q": "苹果"}).json()
        assert body["total"] >= 1
        assert "<script>" not in body["items"][0]["snippet"]
        assert "&lt;script&gt;" in body["items"][0]["snippet"]


class TestRelated:
    def test_related_returns_similar_note(self, client):
        base_id = create_note(client, "苹果 香蕉", "苹果 香蕉").json()["id"]
        create_note(client, "苹果 香蕉 橙子", "苹果 香蕉 橙子")
        body = client.get(f"/api/notes/{base_id}/related").json()
        assert len(body) >= 1
        assert body[0]["score"] > 0

    def test_related_unknown_note_returns_empty(self, client):
        assert client.get("/api/notes/999999/related").json() == []


class TestTagsAndStats:
    def test_tag_counts(self, client):
        create_note(client, "n1", tags=["python", "检索"])
        create_note(client, "n2", tags=["python"])
        counts = {item["name"]: item["count"] for item in client.get("/api/tags").json()}
        assert counts["python"] == 2
        assert counts["检索"] == 1

    def test_stats(self, client):
        create_note(client, "统计用", "一些内容")
        body = client.get("/api/stats").json()
        assert body["note_count"] == 1
        assert body["term_count"] > 0
        assert body["avg_note_length"] > 0


class TestTagSearch:
    def test_tag_only_query_returns_notes(self, client):
        create_note(client, "被标签命中的笔记", "正文随便写", tags=["测试标签甲"])
        body = client.get("/api/search", params={"q": "#测试标签甲"}).json()
        assert body["total"] >= 1
        assert body["items"][0]["title"] == "被标签命中的笔记"

    def test_tag_name_matches_as_plain_text(self, client):
        """标签名进入索引后，不加 # 直接搜也能命中。"""
        create_note(client, "普通标题", "正文里没有这个关键词", tags=["postgres"])
        body = client.get("/api/search", params={"q": "postgres"}).json()
        assert body["total"] >= 1

    def test_unknown_tag_returns_empty(self, client):
        create_note(client, "有标签的", "内容", tags=["python"])
        body = client.get("/api/search", params={"q": "#不存在的标签"}).json()
        assert body["total"] == 0

    def test_tag_only_query_sorted_by_updated_desc(self, client):
        first = create_note(client, "先创建", "内容A", tags=["排序测试"]).json()["id"]
        second = create_note(client, "后创建", "内容B", tags=["排序测试"]).json()["id"]
        body = client.get("/api/search", params={"q": "#排序测试"}).json()
        ids = [item["id"] for item in body["items"]]
        assert ids[0] == second
        assert set(ids) == {first, second}


class TestPartialWordSearch:
    """不完整的词也要能搜到（sql -> MySQL）。"""

    def test_partial_ascii_word(self, client):
        create_note(client, "数据库笔记", "MySQL 连接池配置")
        body = client.get("/api/search", params={"q": "sql"}).json()
        assert body["total"] >= 1
        assert body["items"][0]["title"] == "数据库笔记"

    def test_partial_chinese_word(self, client):
        create_note(client, "中文部分匹配", "连接池参数怎么调")
        body = client.get("/api/search", params={"q": "连接"}).json()
        assert body["total"] >= 1

    def test_partial_matches_tag_name(self, client):
        create_note(client, "带标签的笔记", "正文无关", tags=["MySQL"])
        body = client.get("/api/search", params={"q": "sql"}).json()
        assert body["total"] >= 1


class TestImport:
    def _payload(self, *files):
        return {"files": [{"name": name, "content": content} for name, content in files]}

    def test_import_markdown_file(self, client):
        body = client.post(
            "/api/notes/import",
            json=self._payload(("数据库.md", "# MySQL 索引\n\n索引能加速查询")),
        ).json()
        assert body["imported"] == 1
        assert body["titles"] == ["MySQL 索引"]

        found = client.get("/api/search", params={"q": "索引"}).json()
        assert found["total"] >= 1

    def test_import_json_batch(self, client):
        payload = '[{"title": "批量A", "content": "aaa"}, {"title": "批量B", "content": "bbb", "tags": ["导入"]}]'
        body = client.post("/api/notes/import", json=self._payload(("b.json", payload))).json()
        assert body["imported"] == 2
        tags = {item["name"] for item in client.get("/api/tags").json()}
        assert "导入" in tags

    def test_duplicate_title_is_skipped(self, client):
        client.post("/api/notes/import", json=self._payload(("a.md", "# 重复标题\n正文")))
        body = client.post("/api/notes/import", json=self._payload(("a.md", "# 重复标题\n正文"))).json()
        assert body["imported"] == 0
        assert body["skipped"] == 1

    def test_bad_json_reports_failure(self, client):
        body = client.post("/api/notes/import", json=self._payload(("bad.json", "{ not json"))).json()
        assert body["imported"] == 0
        assert body["failed"][0]["name"] == "bad.json"

    def test_empty_file_list(self, client):
        body = client.post("/api/notes/import", json={"files": []}).json()
        assert body["imported"] == 0
