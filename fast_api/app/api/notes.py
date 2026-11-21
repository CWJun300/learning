"""笔记 CRUD 接口。

注意：路由函数用 def 而不是 async def —— 同步 SQLAlchemy 会阻塞事件循环，
FastAPI 会把 def 端点丢到线程池执行。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, Tag
from app.schemas import NoteCreate, NoteOut, NoteUpdate, PageOut
from app.services.index_manager import index_manager
from app.services.tagging import resolve_tags

router = APIRouter(prefix="/api/notes", tags=["笔记"])


@router.get("", response_model=PageOut[NoteOut], summary="笔记列表（分页 + 标签过滤）")
def list_notes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tag: str | None = Query(None, description="按标签名过滤"),
    db: Session = Depends(get_db),
) -> PageOut[NoteOut]:
    stmt = select(Note)
    if tag:
        stmt = stmt.join(Note.tags).where(Tag.name == tag)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Note.updated_at.desc(), Note.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return PageOut(total=total, page=page, size=size, items=list(items))


@router.post(
    "",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建笔记",
)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)) -> Note:
    note = Note(title=payload.title, content=payload.content)
    note.tags = resolve_tags(db, payload.tags)
    db.add(note)
    db.commit()
    db.refresh(note)
    # 数据库写成功后再更新索引，保证两边不出现"库里有、索引没有"
    index_manager.add_note(note.id, note.full_text)
    return note


@router.get("/{note_id}", response_model=NoteOut, summary="笔记详情")
def get_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"笔记 {note_id} 不存在")
    return note


@router.put("/{note_id}", response_model=NoteOut, summary="更新笔记")
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"笔记 {note_id} 不存在")

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    if payload.tags is not None:
        note.tags = resolve_tags(db, payload.tags)

    db.commit()
    db.refresh(note)
    index_manager.update_note(note.id, note.full_text)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除笔记")
def delete_note(note_id: int, db: Session = Depends(get_db)) -> None:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"笔记 {note_id} 不存在")
    db.delete(note)
    db.commit()
    index_manager.remove_note(note_id)
