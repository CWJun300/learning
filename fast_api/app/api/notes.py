"""笔记 CRUD 接口。

注意：路由函数用 def 而不是 async def —— 同步 SQLAlchemy 会阻塞事件循环，
FastAPI 会把 def 端点丢到线程池执行。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, Tag, TrashedNote
from app.schemas import NoteCreate, NoteLinks, NoteOut, NoteReference, NoteUpdate, PageOut, TrashItem
from app.services.index_manager import index_manager
from app.services.links import linked_note_ids
from app.services.tagging import resolve_tags

router = APIRouter(prefix="/api/notes", tags=["笔记"])


@router.get("", response_model=PageOut[NoteOut], summary="笔记列表（分页 + 标签过滤）")
def list_notes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tag: str | None = Query(None, description="按标签名过滤"),
    db: Session = Depends(get_db),
) -> PageOut[NoteOut]:
    stmt = select(Note).where(Note.active())
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
    index_manager.commit_notes(db, [note])
    db.refresh(note)
    return note


@router.get("/suggestions", response_model=list[NoteReference], summary="按标题选择引用目标")
def suggestions(q: str = "", db: Session = Depends(get_db)):
    stmt = select(Note.id, Note.title).where(Note.active(), Note.title.contains(q, autoescape=True))
    return db.execute(stmt.order_by(Note.updated_at.desc(), Note.id.desc()).limit(20)).all()


@router.get("/trash", response_model=PageOut[TrashItem], summary="回收站")
def list_trash(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(Note.id, Note.title, TrashedNote.deleted_at).join(TrashedNote)
    items = db.execute(stmt.order_by(TrashedNote.deleted_at.desc(), Note.id.desc()).offset((page - 1) * size).limit(size)).all()
    total = db.scalar(select(func.count()).select_from(TrashedNote))
    return PageOut[TrashItem](items=items, total=total, page=page, size=size)


def active_note(db: Session, note_id: int, *, lock: bool = False) -> Note:
    stmt = select(Note).where(Note.id == note_id, Note.active())
    note = db.scalar(stmt.with_for_update() if lock else stmt)
    if note is None:
        raise HTTPException(status_code=404, detail=f"笔记 {note_id} 不存在")
    return note


@router.get("/{note_id}/links", response_model=NoteLinks, summary="引用与反向引用")
def note_links(note_id: int, db: Session = Depends(get_db)):
    source = active_note(db, note_id)
    refs = select(Note.id, Note.title).where(Note.active()).order_by(Note.title, Note.id)
    outgoing = db.execute(refs.where(Note.id.in_(linked_note_ids(source.content)))).all()
    candidates = db.execute(refs.add_columns(Note.content).where(Note.content.contains(f"/notes/{note_id}"))).all()
    incoming = [NoteReference(id=row.id, title=row.title) for row in candidates if note_id in linked_note_ids(row.content)]
    return NoteLinks(outgoing=outgoing, incoming=incoming)


@router.get("/{note_id}", response_model=NoteOut, summary="笔记详情")
def get_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    return active_note(db, note_id)


@router.put("/{note_id}", response_model=NoteOut, summary="更新笔记")
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)) -> Note:
    note = active_note(db, note_id, lock=True)

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    if payload.tags is not None:
        note.tags = resolve_tags(db, payload.tags)

    index_manager.commit_notes(db, [note])
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除笔记")
def delete_note(note_id: int, db: Session = Depends(get_db)) -> None:
    note = active_note(db, note_id, lock=True)
    db.add(TrashedNote(note_id=note.id))
    index_manager.commit_notes(db, removed=[note_id])


@router.post("/{note_id}/restore", response_model=NoteOut, summary="恢复笔记")
def restore_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id, with_for_update=True)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在")
    entry = db.get(TrashedNote, note_id, with_for_update=True)
    if entry is not None:
        db.delete(entry)
        index_manager.commit_notes(db, [note])
    return note
