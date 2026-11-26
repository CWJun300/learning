"""检索接口：查询解析 → 取候选 → 排序 → 过滤 → 高亮。

两种检索路径：
1. 有关键词：走倒排索引 + BM25 打分；
2. 只有 #标签：不参与文本打分，直接按标签把笔记列出来（按更新时间倒序）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, Tag
from app.schemas import PageOut, SearchHit
from app.services.highlight import highlight
from app.services.index_manager import index_manager
from app.services.query_parser import parse_query
from app.services.ranker import BM25Ranker

router = APIRouter(prefix="/api", tags=["检索"])


def _collect_terms(parsed) -> list[str]:
    """把查询结构拆成参与打分的词条。"""
    raw: list[str] = []
    raw.extend(parsed.should)
    raw.extend(parsed.must)
    raw.extend(parsed.phrases)

    tokenizer = index_manager.tokenizer
    terms: list[str] = []
    for item in raw:
        terms.extend(tokenizer.tokenize(item))
    # 去重且保序
    return list(dict.fromkeys(terms))


def _notes_by_tags(db: Session, tags: list[str]) -> list[tuple[int, float]]:
    """纯标签检索：直接按标签取笔记，最近更新的排前面，得分记 0。"""
    stmt = (
        select(Note.id)
        .join(Note.tags)
        .where(Tag.name.in_(tags), Note.active())
        .order_by(Note.updated_at.desc(), Note.id.desc())
    )
    seen: set[int] = set()
    result: list[tuple[int, float]] = []
    for note_id in db.scalars(stmt).all():
        if note_id in seen:
            continue
        seen.add(note_id)
        result.append((note_id, 0.0))
    return result


@router.get("/search", response_model=PageOut[SearchHit], summary="全文检索")
def search_notes(
    q: str = Query(..., min_length=1, description="支持 +必含 / \"短语\" / #标签"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PageOut[SearchHit]:
    parsed = parse_query(q)
    terms = _collect_terms(parsed)

    empty = PageOut(total=0, page=page, size=size, items=[])
    if not terms and not parsed.tags:
        return empty

    index = index_manager.index

    if terms:
        ranked = BM25Ranker(index).search(terms, top_k=2000)
    else:
        # 只有 #标签，没有关键词：按标签列出来即可
        ranked = _notes_by_tags(db, parsed.tags)

    # 1) +必含 词过滤
    if parsed.must and terms:
        must_terms: set[str] = set()
        for word in parsed.must:
            must_terms.update(index_manager.tokenizer.tokenize(word))
        if must_terms:
            ranked = [item for item in ranked if must_terms <= index.doc_terms(item[0])]

    # 2) #标签 过滤（纯标签检索时已经过滤过了）
    if parsed.tags and terms:
        allowed = set(
            db.scalars(select(Note.id).join(Note.tags).where(Note.active(), Tag.name.in_(parsed.tags))).all()
        )
        ranked = [item for item in ranked if item[0] in allowed]

    # 3) 短语过滤：要求原文确实包含该短语
    if parsed.phrases and ranked:
        ids = [doc_id for doc_id, _ in ranked]
        contents = {
            note.id: f"{note.title}\n{note.content}".lower()
            for note in db.scalars(select(Note).where(Note.active(), Note.id.in_(ids))).all()
        }
        ranked = [
            item
            for item in ranked
            if all(phrase.lower() in contents.get(item[0], "") for phrase in parsed.phrases)
        ]

    total = len(ranked)
    window = ranked[(page - 1) * size : page * size]
    if not window:
        return PageOut(total=total, page=page, size=size, items=[])

    ids = [doc_id for doc_id, _ in window]
    notes = {note.id: note for note in db.scalars(select(Note).where(Note.active(), Note.id.in_(ids))).all()}

    hits: list[SearchHit] = []
    for doc_id, score in window:
        note = notes.get(doc_id)
        if note is None:  # 索引与数据库短暂不一致时跳过，而不是抛错
            continue
        hits.append(
            SearchHit(
                id=note.id,
                title=note.title,
                snippet=highlight(note.content or note.title, terms),
                score=round(score, 4),
                tags=[tag.name for tag in note.tags],
            )
        )

    return PageOut(total=total, page=page, size=size, items=hits)


@router.get("/notes/{note_id}/related", response_model=list[SearchHit], summary="相似笔记")
def related_notes(
    note_id: int,
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[SearchHit]:
    from app.services.recommend import recommend_related

    index = index_manager.index
    pairs = recommend_related(index, note_id, top_k=top_k)
    if not pairs:
        return []

    ids = [doc_id for doc_id, _ in pairs]
    notes = {note.id: note for note in db.scalars(select(Note).where(Note.active(), Note.id.in_(ids))).all()}
    hits: list[SearchHit] = []
    for doc_id, score in pairs:
        note = notes.get(doc_id)
        if note is None:
            continue
        hits.append(
            SearchHit(
                id=note.id,
                title=note.title,
                snippet=highlight(note.content or note.title, [], context=80),
                score=round(score, 4),
                tags=[tag.name for tag in note.tags],
            )
        )
    return hits
