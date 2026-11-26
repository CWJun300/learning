"""安装随应用分发的自测题。题卡、首次需要的来源笔记和安装标记一起提交。"""

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Note, ReviewCard, StarterBankInstall, TrashedNote
from app.services.index_manager import index_manager
from app.services.tagging import resolve_tags

VERSION = 1


@lru_cache(maxsize=1)
def lessons() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "data" / "starter_cards.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def objective_rules() -> dict[tuple[str, str], dict]:
    # 用原始题干和参考答案识别旧库及备份中的同一道题，保留原题卡 ID 与进度。
    return {(card["question"], card["answer"]): card["exercise"]
            for lesson in lessons() for card in lesson["cards"] if "exercise" in card}


def first_review_size(db: Session) -> int:
    if db.get(StarterBankInstall, VERSION) or db.scalar(select(ReviewCard.id).limit(1)):
        return 0
    hidden = set(db.scalars(select(Note.title).join(TrashedNote)))
    if hidden:
        hidden.difference_update(db.scalars(select(Note.title).where(Note.title.in_(hidden), Note.active())))
    return sum(len(lesson["cards"]) for lesson in lessons() if lesson["title"] not in hidden)


def install(db: Session, due: date) -> int:
    if db.get(StarterBankInstall, VERSION):
        return 0
    db.add(StarterBankInstall(version=VERSION))
    try:
        db.flush()
    except IntegrityError:
        # 两个页面同时开始时，主键确保只有一个事务负责写入。
        db.rollback()
        if db.get(StarterBankInstall, VERSION):
            return 0
        raise

    titles = [lesson["title"] for lesson in lessons()]
    questions = [c["question"] for lesson in lessons() for c in lesson["cards"]]
    prior = db.execute(select(ReviewCard.note_id, ReviewCard.question).where(ReviewCard.question.in_(questions))).all()
    existing = set(prior)
    sources = {q: nid for nid, q in prior}
    trashed = set(db.scalars(select(TrashedNote.note_id)))
    notes = {}
    for note in db.scalars(select(Note).where(Note.title.in_(titles)).order_by(Note.id)):
        if note.title not in notes or notes[note.title].id in trashed:
            notes[note.title] = note
    new_notes = []
    added = 0
    for lesson in lessons():
        # 从整库备份恢复后，题目可能仍指向用户已经改名的笔记。
        note = notes.get(lesson["title"])
        if note is None:
            old_ids = {sources.get(c["question"]) for c in lesson["cards"]}
            if len(old_ids) == 1 and None not in old_ids:
                note = db.get(Note, old_ids.pop())
        if note is None:
            note = Note(title=lesson["title"], content=lesson["text"])
            note.tags = resolve_tags(db, list(dict.fromkeys(["原创讲义", *lesson["tags"]])))
            db.add(note)
            db.flush()
            new_notes.append(note)
        if note.id in trashed:
            continue
        for card in lesson["cards"]:
            if (note.id, card["question"]) not in existing:
                db.add(ReviewCard(note_id=note.id, due=due, question=card["question"], answer=card["answer"]))
                added += 1
    index_manager.commit_notes(db, new_notes)
    return added
