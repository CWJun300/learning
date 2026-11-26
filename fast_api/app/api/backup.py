"""版本化 JSON 备份。保留原始笔记 ID，正文内的引用在恢复后仍然有效。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, NaiveDatetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, TrashedNote
from app.services.index_manager import index_manager
from app.services.tagging import resolve_tags
from app.services.study_backup import StudyArchive, export_study, restore_study

router = APIRouter(prefix="/api/backup", tags=["备份"])


class BackupNote(BaseModel):
    id: int = Field(gt=0, le=2**63 - 1)
    title: str = Field(min_length=1, max_length=200)
    content: str
    tags: list[Annotated[str, Field(min_length=1, max_length=50)]]
    created_at: NaiveDatetime
    updated_at: NaiveDatetime
    deleted_at: NaiveDatetime | None


class Backup(BaseModel):
    format: Literal["personal-kb"]
    version: Literal[1]
    notes: list[BackupNote]


class LearningBackup(BaseModel):
    format: Literal["personal-kb"]
    version: Literal[2]
    notes: list[BackupNote]
    study: StudyArchive


def snapshot(note: Note, deleted_at) -> BackupNote:
    return BackupNote(id=note.id, title=note.title, content=note.content,
                      tags=sorted(tag.name for tag in note.tags), created_at=note.created_at,
                      updated_at=note.updated_at, deleted_at=deleted_at)


@router.get("", response_model=Backup | LearningBackup, summary="下载整库 JSON")
def export_backup(response: Response, db: Session = Depends(get_db)):
    rows = db.execute(select(Note, TrashedNote.deleted_at).outerjoin(TrashedNote).order_by(Note.id))
    response.headers["Content-Disposition"] = 'attachment; filename="knowledge-base.json"'
    notes = [snapshot(note, deleted) for note, deleted in rows]
    study = export_study(db)
    if study.topics or study.cards:
        return LearningBackup(format="personal-kb", version=2, notes=notes, study=study)
    return Backup(format="personal-kb", version=1, notes=notes)


@router.post("/restore", summary="恢复备份，跳过完全相同的笔记")
def restore_backup(payload: Backup | LearningBackup, db: Session = Depends(get_db)):
    ids = [item.id for item in payload.notes]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "备份中存在重复的笔记 ID")

    existing = {note.id: snapshot(note, deleted) for note, deleted in db.execute(
        select(Note, TrashedNote.deleted_at).outerjoin(TrashedNote).where(Note.id.in_(ids))
    )}
    new = []
    for item in payload.notes:
        if item.id not in existing:
            new.append(item)
        elif existing[item.id] != item.model_copy(update={"tags": sorted(item.tags)}):
            raise HTTPException(409, f"笔记 #{item.id} 与当前库冲突，未写入任何笔记。可在空库中完整恢复。")

    active = []
    try:
        for item in new:
            note = Note(id=item.id, title=item.title, content=item.content,
                        created_at=item.created_at, updated_at=item.updated_at)
            note.tags = resolve_tags(db, item.tags)
            db.add(note)
            db.flush()
            if item.deleted_at is None:
                active.append(note)
            else:
                db.add(TrashedNote(note_id=note.id, deleted_at=item.deleted_at))
        if isinstance(payload, LearningBackup):
            restore_study(db, payload.study, set(ids))
        index_manager.commit_notes(db, active)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "数据发生冲突，本次恢复已撤销") from exc

    return {"restored": len(new), "skipped": len(ids) - len(new)}
