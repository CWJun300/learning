"""专题阅读与按日安排的自测。回收站内笔记保留进度，恢复后重新出现。"""

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.notes import active_note
from app.db import get_db
from app.models import Note, ReviewCard, Topic, TopicItem
from app.services import starter_bank

router = APIRouter(prefix="/api/study", tags=["学习"])
ReadingState = Literal["unread", "read", "review"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
LOCAL_TIME = timezone(timedelta(hours=8))


def today() -> date:
    return datetime.now(LOCAL_TIME).date()


class NoteSelection(BaseModel):
    note_ids: list[int]


class NewTopic(NoteSelection):
    name: Name


class Reading(BaseModel):
    status: ReadingState | None = None


class NewCard(BaseModel):
    note_id: int
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CardRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)


class Grade(CardRevision):
    remembered: bool


class Attempt(CardRevision):
    response: str = Field(min_length=1, max_length=256)


def topic_or_404(db: Session, topic_id: int, *, lock: bool = False) -> Topic:
    topic = db.get(Topic, topic_id, with_for_update=lock)
    if topic is None:
        raise HTTPException(404, "专题不存在")
    return topic


def topic_views(db: Session, topics: list[Topic]) -> list[dict]:
    views = {t.id: dict(id=t.id, name=t.name, current_note_id=t.current_note_id, items=[]) for t in topics}
    rows = db.execute(
        select(TopicItem, Note.title).join(Note).where(TopicItem.topic_id.in_(views), Note.active())
        .order_by(TopicItem.topic_id, TopicItem.position, TopicItem.note_id)
    )
    for item, title in rows:
        views[item.topic_id]["items"].append(dict(note_id=item.note_id, title=title, status=item.status))
    for view in views.values():
        if view["current_note_id"] not in {i["note_id"] for i in view["items"]}:
            view["current_note_id"] = None
    return list(views.values())


def append_items(db: Session, topic: Topic, ids: list[int]) -> None:
    selected = list(dict.fromkeys(ids))
    available = set(db.scalars(select(Note.id).where(Note.id.in_(selected), Note.active())))
    if available != set(selected):
        raise HTTPException(409, "所选笔记已被移走，请刷新后重试")
    rows = list(db.scalars(select(TopicItem).where(TopicItem.topic_id == topic.id)))
    existing = {item.note_id for item in rows}
    position = max((item.position for item in rows), default=-1)
    for note_id in selected:
        if note_id not in existing:
            position += 1
            db.add(TopicItem(topic_id=topic.id, note_id=note_id, position=position))


@router.get("/topics")
def topics(db: Session = Depends(get_db)):
    rows = db.scalars(select(Topic).order_by(Topic.updated_at.desc(), Topic.id.desc())).all()
    return topic_views(db, rows)


@router.post("/topics", status_code=201)
def create_topic(payload: NewTopic, db: Session = Depends(get_db)):
    topic = Topic(name=payload.name)
    db.add(topic)
    db.flush()
    append_items(db, topic, payload.note_ids)
    db.commit()
    return {"id": topic.id}


@router.get("/topics/{topic_id}")
def topic_details(topic_id: int, db: Session = Depends(get_db)):
    view = topic_views(db, [topic_or_404(db, topic_id)])[0]
    counts = select(func.count(ReviewCard.id), func.count(case((ReviewCard.wrong.is_(True), 1))))
    view["card_count"], view["wrong_count"] = db.execute(cards_for_topic(counts, topic_id)).one()
    return view


@router.post("/topics/{topic_id}/items", status_code=204)
def add_items(topic_id: int, payload: NoteSelection, db: Session = Depends(get_db)):
    topic = topic_or_404(db, topic_id, lock=True)
    append_items(db, topic, payload.note_ids)
    db.commit()


@router.put("/topics/{topic_id}/order", status_code=204)
def order_items(topic_id: int, payload: NoteSelection, db: Session = Depends(get_db)):
    topic_or_404(db, topic_id, lock=True)
    rows = db.scalars(select(TopicItem).join(Note).where(TopicItem.topic_id == topic_id, Note.active())).all()
    by_note = {row.note_id: row for row in rows}
    if len(payload.note_ids) != len(rows) or set(payload.note_ids) != set(by_note):
        raise HTTPException(409, "专题内容已变化，请刷新后重新排序")
    for position, note_id in zip(sorted(row.position for row in rows), payload.note_ids):
        by_note[note_id].position = position
    db.commit()


@router.delete("/topics/{topic_id}/items/{note_id}", status_code=204)
def remove_item(topic_id: int, note_id: int, db: Session = Depends(get_db)):
    topic = topic_or_404(db, topic_id, lock=True)
    item = db.get(TopicItem, (topic_id, note_id))
    if item:
        db.delete(item)
    if topic.current_note_id == note_id:
        topic.current_note_id = None
    db.commit()


@router.patch("/topics/{topic_id}/reading/{note_id}", status_code=204)
def reading(topic_id: int, note_id: int, payload: Reading, db: Session = Depends(get_db)):
    topic = topic_or_404(db, topic_id, lock=True)
    active_note(db, note_id)
    item = db.get(TopicItem, (topic_id, note_id))
    if item is None:
        raise HTTPException(404, "此笔记不在该专题中")
    if payload.status is not None:
        item.status = payload.status
    topic.current_note_id = note_id
    topic.updated_at = datetime.now(LOCAL_TIME).replace(tzinfo=None)
    db.commit()


@router.post("/cards", status_code=201)
def create_card(payload: NewCard, db: Session = Depends(get_db)):
    active_note(db, payload.note_id)
    card = ReviewCard(**payload.model_dump(), due=today())
    db.add(card)
    db.commit()
    return {"id": card.id}


@router.post("/starter", summary="开始基础自测")
def start_starter_bank(db: Session = Depends(get_db)):
    return {"added": starter_bank.install(db, today())}


@router.get("/counts")
def review_counts(db: Session = Depends(get_db)):
    cards = select(func.count(ReviewCard.id)).join(Note).where(Note.active())
    counts = {
        "due": db.scalar(cards.where(ReviewCard.due <= today())),
        "wrong": db.scalar(cards.where(ReviewCard.wrong.is_(True))),
    }
    if not counts["due"]:
        size = starter_bank.first_review_size(db)
        if size:
            counts["starter_size"] = size
    return counts


def cards_for_topic(stmt, topic_id: int):
    return (stmt.select_from(ReviewCard).join(Note, ReviewCard.note_id == Note.id)
            .join(TopicItem, TopicItem.note_id == Note.id).where(TopicItem.topic_id == topic_id, Note.active()))


def review_view(card: ReviewCard, title: str) -> dict:
    data = dict(id=card.id, note_id=card.note_id, title=title, revision=card.revision)
    rule = starter_bank.objective_rules().get((card.question, card.answer))
    if rule is None:
        return dict(data, kind="self", question=card.question, answer=card.answer)
    data.update(kind=rule["kind"], question=rule["prompt"])
    if rule["kind"] == "choice":
        data["options"] = rule["options"]
    return data


@router.get("/cards")
def review_cards(mode: Literal["due", "wrong", "all"] = "due", topic_id: int | None = None,
                 db: Session = Depends(get_db)):
    stmt = select(ReviewCard, Note.title)
    if topic_id is not None:
        topic_or_404(db, topic_id)
        stmt = cards_for_topic(stmt, topic_id).order_by(TopicItem.position, ReviewCard.id)
    elif mode == "all":
        raise HTTPException(422, "练习全部题目时请选择专题")
    else:
        stmt = stmt.join(Note).where(Note.active()).order_by(ReviewCard.due, ReviewCard.id)
    if mode == "wrong":
        stmt = stmt.where(ReviewCard.wrong.is_(True))
    elif mode == "due":
        stmt = stmt.where(ReviewCard.due <= today())
    return [review_view(card, title) for card, title in db.execute(stmt)]


def check_attempt(rule: dict, response: str) -> bool:
    if rule["kind"] == "choice":
        if response not in rule["options"]:
            raise HTTPException(422, "请选择题目中的一个选项")
        return response == rule["key"]
    number = unicodedata.normalize("NFKC", response).strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", number):
        raise HTTPException(422, "请填写整数或小数")
    return Decimal(number) == Decimal(rule["key"])


@router.post("/cards/{card_id}/grade")
def grade_card(card_id: int, payload: Grade | Attempt, db: Session = Depends(get_db)):
    card = db.get(ReviewCard, card_id, with_for_update=True)
    if card is None:
        raise HTTPException(404, "自测题不存在")
    active_note(db, card.note_id)
    if payload.revision != card.revision:
        raise HTTPException(409, "这道题已在其他页面作答，请刷新题目")
    rule = starter_bank.objective_rules().get((card.question, card.answer))
    result = {}
    if rule is not None and isinstance(payload, Attempt):
        remembered = check_attempt(rule, payload.response)
        result.update(correct=remembered, correct_answer=rule["key"], explanation=card.answer)
    elif rule is None and isinstance(payload, Grade):
        remembered = payload.remembered
    else:
        raise HTTPException(422, "请按题型提交答案")
    intervals = (1, 3, 7, 14, 30)
    card.streak = card.streak + 1 if remembered else 0
    interval = intervals[min(card.streak, len(intervals)) - 1] if card.streak else 1
    card.due = today() + timedelta(days=interval)
    card.wrong = not remembered
    card.revision += 1
    db.commit()
    return dict(result, due=card.due, wrong=card.wrong)
