"""专题、答题与版本化备份的集成测试。"""

from datetime import timedelta

import pytest

from app.api.study import today

pytestmark = pytest.mark.db
BASE = "/api/study"


def note(client, title):
    return client.post("/api/notes", json={"title": title, "content": "课程正文"}).json()["id"]


def topic(client, ids):
    response = client.post(BASE + "/topics", json={"name": "复习", "note_ids": ids})
    assert response.status_code == 201
    return BASE + "/topics/" + str(response.json()["id"])


def test_topic_progress_order_trash_and_resume(client):
    a, b = note(client, "第一课"), note(client, "第二课")
    first, second = topic(client, [a, b, a]), topic(client, [a])
    assert client.put(first + "/order", json={"note_ids": [b, a]}).status_code == 204
    assert client.put(first + "/order", json={"note_ids": [a, a]}).status_code == 409
    assert client.patch(first + f"/reading/{a}", json={"status": "review"}).status_code == 204
    data = client.get(first).json()
    assert data["current_note_id"] == a
    assert [i["note_id"] for i in data["items"]] == [b, a]
    assert data["items"][1]["status"] == "review"
    assert client.get(second).json()["items"][0]["status"] == "unread"
    client.delete(f"/api/notes/{a}")
    assert client.get(first).json()["current_note_id"] is None
    assert client.get(second).json()["items"] == []
    client.post(f"/api/notes/{a}/restore")
    assert client.get(first).json() == data
    assert client.delete(first + f"/items/{a}").status_code == 204
    assert client.get(first).json()["current_note_id"] is None
    assert client.get(second).json()["items"][0]["note_id"] == a


def test_review_scheduling_retries_and_trash(client):
    nid = note(client, "来源")
    result = client.post(BASE + "/cards", json={"note_id": nid, "question": "什么是索引？", "answer": "答案"})
    assert result.status_code == 201
    url = BASE + f"/cards/{result.json()['id']}/grade"
    wrong = {"remembered": False, "revision": 0}
    assert client.get(BASE + "/counts").json() == {"due": 1, "wrong": 0}
    assert client.post(url, json=wrong).json()["due"] == (today() + timedelta(days=1)).isoformat()
    assert client.post(url, json=wrong).status_code == 409
    assert client.get(BASE + "/counts").json() == {"due": 0, "wrong": 1}
    client.delete(f"/api/notes/{nid}")
    assert client.get(BASE + "/cards?mode=wrong").json() == []
    client.post(f"/api/notes/{nid}/restore")
    card = client.get(BASE + "/cards?mode=wrong").json()[0]
    assert card["note_id"] == nid
    client.post(url, json={"remembered": True, "revision": card["revision"]})
    assert client.get(BASE + "/counts").json() == {"due": 0, "wrong": 0}


def test_learning_backup_restores_progress_and_rejects_conflicts_atomically(client):
    nid = note(client, "课文")
    saved_topic = dict(id=81, name="期末", updated_at="2026-11-20T12:00:00", current_note_id=nid,
                       items=[dict(position=0, status="review", note_id=nid)])
    saved_card = dict(id=73, note_id=nid, question="例题", answer="原文", due=today().isoformat(),
                      wrong=True, streak=0, revision=3)
    backup = client.get("/api/backup").json()
    assert backup["version"] == 1
    backup.update(version=2, study={"topics": [saved_topic], "cards": [saved_card]})
    assert client.post("/api/backup/restore", json=backup).status_code == 200
    assert client.get("/api/backup").json() == backup
    assert client.post("/api/backup/restore", json=backup).status_code == 200
    backup["study"]["topics"].append(dict(saved_topic, id=82))
    backup["study"]["cards"][0]["answer"] = "冲突"
    assert client.post("/api/backup/restore", json=backup).status_code == 409
    assert client.get(BASE + "/topics/82").status_code == 404
