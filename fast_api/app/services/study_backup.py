"""专题与自测数据与笔记使用同一恢复事务。"""

from datetime import date
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, NaiveDatetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReviewCard, Topic, TopicItem

PositiveId = Annotated[int, Field(gt=0)]


class SavedItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    note_id: PositiveId
    position: int = Field(ge=0)
    status: Literal["unread", "read", "review"]


class SavedTopic(BaseModel):
    id: PositiveId
    name: str = Field(min_length=1, max_length=120)
    updated_at: NaiveDatetime
    current_note_id: PositiveId | None
    items: list[SavedItem]


class SavedCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: PositiveId
    note_id: PositiveId
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1)
    due: date
    wrong: bool
    streak: int = Field(ge=0)
    revision: int = Field(ge=0)


class StudyArchive(BaseModel):
    topics: list[SavedTopic]
    cards: list[SavedCard]


def export_study(db: Session) -> StudyArchive:
    items_by_topic = {}
    for row in db.scalars(select(TopicItem).order_by(TopicItem.topic_id, TopicItem.position)):
        items_by_topic.setdefault(row.topic_id, []).append(SavedItem.model_validate(row))
    topics = [
        SavedTopic(id=t.id, name=t.name, current_note_id=t.current_note_id, updated_at=t.updated_at,
                   items=items_by_topic.get(t.id, []))
        for t in db.scalars(select(Topic).order_by(Topic.id))
    ]
    cards = [SavedCard.model_validate(c) for c in db.scalars(select(ReviewCard).order_by(ReviewCard.id))]
    return StudyArchive(topics=topics, cards=cards)


def missing_records(incoming, existing):
    by_id = {row.id: row for row in existing}
    if len({row.id for row in incoming}) != len(incoming):
        raise HTTPException(422, "学习数据有重复 ID")
    for row in incoming:
        if row.id not in by_id:
            yield row
        elif row != by_id[row.id]:
            raise HTTPException(409, "学习记录与当前库冲突，本次恢复已撤销")


def restore_study(db: Session, archive: StudyArchive, note_ids: set[int]) -> None:
    existing = export_study(db)
    for t in missing_records(archive.topics, existing.topics):
        members = {item.note_id for item in t.items}
        positions = {item.position for item in t.items}
        if (not members <= note_ids or len(members) != len(t.items) or len(positions) != len(t.items)
                or (t.current_note_id is not None and t.current_note_id not in members)):
            raise HTTPException(422, "备份中的专题目录无效")
        db.add(Topic(**t.model_dump(exclude={"items"})))
        db.flush()
        db.add_all(TopicItem(topic_id=t.id, **item.model_dump()) for item in t.items)
    for card in missing_records(archive.cards, existing.cards):
        if card.note_id not in note_ids:
            raise HTTPException(422, "自测题的来源笔记缺失")
        db.add(ReviewCard(**card.model_dump()))
