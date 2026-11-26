"""通过 API 验证链接、回收站和备份的组合行为。"""

import pytest

pytestmark = pytest.mark.db


def create(client, title, content="", tags=None):
    result = client.post("/api/notes", json={"title": title, "content": content, "tags": tags or []})
    assert result.status_code == 201
    return result.json()["id"]


def test_links_survive_rename_edit_and_trash(client):
    target = create(client, "索引", tags=["课程"])
    path = f"/notes/{target}"
    source = create(client, "复习", f"[索引]({path})")
    create(client, "代码示例", f"`[索引]({path})`\n\n```md\n[索引]({path})\n```")
    client.put(f"/api/notes/{target}", json={"title": "B+ 树"})
    assert client.get("/api/notes/suggestions", params={"q": "B+"}).json() == [{"id": target, "title": "B+ 树"}]
    assert client.get(f"/api/notes/{source}/links").json()["outgoing"] == [{"id": target, "title": "B+ 树"}]
    assert client.get(f"/api/notes/{target}/links").json()["incoming"] == [{"id": source, "title": "复习"}]

    assert client.delete(f"/api/notes/{target}").status_code == 204
    assert client.get("/api/notes/trash").json()["items"][0]["id"] == target
    assert client.get(f"/api/notes/{source}/links").json()["outgoing"] == []
    assert client.get("/api/search", params={"q": "#课程"}).json()["total"] == 0
    assert client.get("/api/tags").json() == []
    assert client.get("/api/notes/suggestions", params={"q": "B+"}).json() == []
    assert client.post(f"/api/notes/{target}/restore").status_code == 200
    assert client.get("/api/search", params={"q": "#课程"}).json()["items"][0]["id"] == target
    assert client.get("/api/notes/trash").json()["total"] == 0
    assert client.get(f"/api/notes/{target}/links").json()["incoming"][0]["id"] == source
    client.put(f"/api/notes/{source}", json={"content": "已移除引用"})
    assert client.get(f"/api/notes/{target}/links").json()["incoming"] == []


def test_backup_roundtrip_and_retry(client):
    fields = dict(title="同名", tags=["复习"], created_at="2026-01-02T12:00:00",
                  updated_at="2026-02-03T12:00:00", deleted_at=None)
    notes = [dict(fields, id=101, content="alphabet"), dict(fields, id=202, content="[示例](/notes/101)"),
             dict(fields, id=303, content="recycledonly", deleted_at="2026-03-04T12:00:00")]
    backup = {"format": "personal-kb", "version": 1, "notes": notes}
    assert client.post("/api/backup/restore", json=backup).json() == {"restored": 3, "skipped": 0}
    assert client.get("/api/backup").json() == backup
    assert client.post("/api/backup/restore", json=backup).json() == {"restored": 0, "skipped": 3}
    assert client.get("/api/notes/101/links").json()["incoming"][0]["id"] == 202
    assert client.get("/api/search?q=alphabet").json()["total"] == 1
    assert client.get("/api/search?q=recycledonly").json()["total"] == 0
    assert client.get("/api/stats").json()["note_count"] == 2
    assert client.get("/api/notes/trash").json()["items"][0]["id"] == 303

    conflicting = dict(backup, notes=[dict(notes[0], id=404), dict(notes[1], title="冲突")])
    assert client.post("/api/backup/restore", json=conflicting).status_code == 409
    assert client.get("/api/backup").json() == backup
    assert client.post("/api/backup/restore", json=dict(backup, notes=[notes[0]] * 2)).status_code == 422
