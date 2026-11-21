"""批量导入接口。

前端用 FileReader 读文件内容后以 JSON 提交，因此不需要 python-multipart 依赖，
部署和测试都更简单。
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note
from app.schemas import ImportResult, ImportFailure, ImportRequest
from app.services.importer import parse_any
from app.services.index_manager import index_manager
from app.services.tagging import resolve_tags

router = APIRouter(prefix="/api", tags=["批量导入"])

MAX_FILES = 50
MAX_FILE_BYTES = 1_000_000  # 单文件 1MB


@router.post(
    "/notes/import",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="批量导入笔记（md / txt / json）",
)
def import_notes(payload: ImportRequest, db: Session = Depends(get_db)) -> ImportResult:
    failures: list[ImportFailure] = []
    imported_titles: list[str] = []
    skipped_titles: list[str] = []

    if len(payload.files) > MAX_FILES:
        return ImportResult(
            imported=0,
            skipped=0,
            failed=[ImportFailure(name="*", reason=f"一次最多导入 {MAX_FILES} 个文件")],
            titles=[],
        )

    existing_titles = set(db.scalars(select(Note.title)).all())
    created: list[Note] = []

    for item in payload.files:
        name = item.name or "未命名"
        content = item.content or ""

        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            failures.append(ImportFailure(name=name, reason="文件超过 1MB"))
            continue

        try:
            parsed_notes = parse_any(name, content)
        except ValueError as exc:
            failures.append(ImportFailure(name=name, reason=str(exc)))
            continue

        for parsed in parsed_notes:
            title = (parsed.title or "").strip()
            if not title:
                failures.append(ImportFailure(name=name, reason="标题为空"))
                continue
            if title in existing_titles:
                skipped_titles.append(title)
                continue

            note = Note(title=title[:200], content=parsed.content or "")
            note.tags = resolve_tags(db, parsed.tags)
            db.add(note)
            db.flush()
            created.append(note)
            existing_titles.add(title)
            imported_titles.append(title)

    db.commit()

    # 数据库提交成功后再更新内存索引
    for note in created:
        index_manager.add_note(note.id, note.full_text)

    return ImportResult(
        imported=len(imported_titles),
        skipped=len(skipped_titles),
        failed=failures,
        titles=imported_titles,
    )
