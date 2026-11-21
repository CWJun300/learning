"""标签读取或创建：笔记新建与批量导入共用。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tag


def resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    """按名字取标签，不存在则新建；去重并保持传入顺序。"""
    cleaned = [name.strip() for name in names if name and name.strip()]
    if not cleaned:
        return []

    unique = list(dict.fromkeys(cleaned))
    existing = {tag.name: tag for tag in db.scalars(select(Tag).where(Tag.name.in_(unique))).all()}

    tags: list[Tag] = []
    for name in unique:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags
