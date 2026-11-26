"""标签与统计接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, Tag, note_tags
from app.schemas import StatsOut, TagCount
from app.services.index_manager import index_manager

router = APIRouter(prefix="/api", tags=["标签与统计"])


@router.get("/tags", response_model=list[TagCount], summary="标签列表（含引用计数）")
def list_tags(db: Session = Depends(get_db)) -> list[TagCount]:
    stmt = (
        select(Tag.name, func.count(note_tags.c.note_id).label("cnt"))
        .join(note_tags, Tag.id == note_tags.c.tag_id)
        .join(Note, Note.id == note_tags.c.note_id)
        .where(Note.active())
        .group_by(Tag.name)
        .order_by(func.count(note_tags.c.note_id).desc(), Tag.name)
    )
    return [TagCount(name=name, count=count) for name, count in db.execute(stmt).all()]


@router.get("/stats", response_model=StatsOut, summary="知识库统计")
def stats(db: Session = Depends(get_db)) -> StatsOut:
    note_count = db.scalar(select(func.count(Note.id)).where(Note.active())) or 0
    index = index_manager.index
    if note_count:
        avg_len = sum(index.doc_length(nid) for nid in index.doc_ids()) / note_count
    else:
        avg_len = 0.0
    return StatsOut(
        note_count=note_count,
        term_count=len(index.terms()),
        avg_note_length=round(avg_len, 2),
    )
