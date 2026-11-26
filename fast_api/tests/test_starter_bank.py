import pytest

pytestmark = pytest.mark.db


def test_first_session_has_starter_cards_with_sources(client):
    assert client.get("/api/study/counts").json()["starter_size"] == 50
    assert client.post("/api/study/starter").json() == {"added": 50}
    cards = client.get("/api/study/cards").json()
    assert len(cards) == len({card["question"] for card in cards}) == 50
    assert len({card["note_id"] for card in cards}) == 25
    assert all(card["title"].strip() for card in cards)
    manual = [card for card in cards if card["kind"] == "self"]
    assert len(manual) == 35 and all(card["answer"].strip() for card in manual)
    assert all("answer" not in card and "key" not in card for card in cards if card["kind"] != "self")
    assert client.get("/api/stats").json()["note_count"] == 25
    assert client.get("/api/search?q=DictReader").json()["total"] >= 1
    first = manual[0]
    grade = client.post(f"/api/study/cards/{first['id']}/grade", json={"remembered": False, "revision": 0})
    assert grade.status_code == 200
    assert client.post("/api/study/starter").json() == {"added": 0}
    assert client.get("/api/study/counts").json() == {"due": 49, "wrong": 1}
    assert client.get("/api/study/cards?mode=wrong").json()[0]["revision"] == 1


def test_existing_and_trashed_sources_are_respected(client):
    from app.services.starter_bank import lessons

    active, archived = lessons()[:2]
    ids = [client.post("/api/notes", json={"title": lesson["title"], "content": "用户已编辑的笔记"}).json()["id"]
           for lesson in (active, archived)]
    client.delete(f"/api/notes/{ids[1]}")
    assert client.get("/api/study/counts").json()["starter_size"] == 48
    assert client.post("/api/study/starter").json() == {"added": 48}
    assert client.get(f"/api/notes/{ids[0]}").json()["content"] == "用户已编辑的笔记"
    assert len([c for c in client.get("/api/study/cards").json() if c["note_id"] == ids[0]]) == 2
    assert client.get("/api/notes/trash").json()["items"][0]["id"] == ids[1]


def test_automatic_grading_and_topic_scope(client):
    base = "/api/study"
    client.post(base + "/starter")
    cards = client.get(base + "/cards").json()
    choice = next(c for c in cards if "零人及格" in c["question"])
    number = next(c for c in cards if "对这一组执行" in c["question"])
    assert choice["note_id"] == number["note_id"]
    topic = client.post(base + "/topics", json={"name": "SQL", "note_ids": [number["note_id"]]}).json()["id"]
    other = client.post(base + "/topics", json={"name": "算法", "note_ids": [cards[0]["note_id"]]}).json()["id"]

    def queue(mode, topic_id=topic):
        return client.get(base + "/cards", params={"mode": mode, "topic_id": topic_id}).json()

    def submit(card, revision, **data):
        return client.post(base + f"/cards/{card['id']}/grade", json=dict(revision=revision, **data))

    assert queue("all") == [choice, number]
    assert client.get(base + "/cards?mode=all").status_code == 422
    assert client.get(base + "/cards?topic_id=999999").status_code == 404
    assert submit(number, 0, response="一字节").status_code == 422
    assert submit(choice, 0, response="其他").status_code == 422
    assert submit(choice, 0, remembered=True).status_code == 422
    assert submit(choice, 0, response=choice["options"][0], remembered=True).status_code == 422
    answer = submit(choice, 0, response="WHERE 条件").json()
    assert answer["wrong"] and not answer["correct"] and answer["correct_answer"] in choice["options"]
    assert "COUNT" in answer["explanation"]
    assert submit(choice, 0, response=answer["correct_answer"]).status_code == 409
    assert submit(number, 0, response=" １．００ ").json()["correct"]
    assert not queue("due") and len(queue("all")) == 2
    assert [c["id"] for c in queue("wrong")] == [choice["id"]]
    assert not queue("wrong", other)
    details = base + f"/topics/{topic}"
    assert client.get(details).json()["wrong_count"] == 1
    assert submit(choice, 1, response=answer["correct_answer"]).json()["correct"]
    assert not queue("wrong")
    assert client.get(details).json()["card_count"] == 2
    client.delete(f"/api/notes/{choice['note_id']}")
    assert not queue("all")
    assert client.get(details).json()["card_count"] == 0
    client.post(f"/api/notes/{choice['note_id']}/restore")
    assert len(queue("all")) == 2


def test_all_objective_answer_keys(client):
    from app.services.starter_bank import objective_rules

    rules = {rule["prompt"]: rule for rule in objective_rules().values()}
    assert len(rules) == 15
    client.post("/api/study/starter")
    for card in client.get("/api/study/cards").json():
        if card["kind"] == "self":
            continue
        rule = rules.pop(card["question"])
        if card["kind"] == "choice":
            assert len(set(card["options"])) == len(card["options"]) >= 2
            assert rule["key"] in card["options"]
        result = client.post(f"/api/study/cards/{card['id']}/grade", json={"revision": 0, "response": rule["key"]})
        assert result.status_code == 200 and result.json()["correct"]
        assert result.json()["explanation"].strip()
    assert not rules
