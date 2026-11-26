"""ORM 模型：notes / tags / note_tags。"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
    select,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# 笔记正文用 MEDIUMTEXT（最大 16MB），其他数据库退回普通 TEXT
LongText = Text().with_variant(MEDIUMTEXT(), "mysql")
NoteId = BigInteger().with_variant(Integer(), "sqlite")

note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", BigInteger, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class TrashedNote(Base):
    __tablename__ = "note_trash"

    note_id: Mapped[int] = mapped_column(NoteId, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(NoteId, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(LongText, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=note_tags,
        back_populates="notes",
        lazy="selectin",
    )

    @property
    def full_text(self) -> str:
        """参与检索的文本。

        标题重复两次用来提高权重；标签名也一并纳入，
        这样直接搜「后端」也能命中打了 #后端 标签的笔记。
        """
        tag_names = " ".join(tag.name for tag in self.tags)
        return f"{self.title} {self.title} {self.content} {tag_names}"

    @classmethod
    def active(cls):
        return ~select(TrashedNote.note_id).where(TrashedNote.note_id == cls.id).exists()


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    notes: Mapped[list[Note]] = relationship(
        secondary=note_tags,
        back_populates="tags",
    )


class Topic(Base):
    __tablename__ = "study_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    current_note_id: Mapped[int | None] = mapped_column(NoteId, ForeignKey("notes.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TopicItem(Base):
    __tablename__ = "study_topic_items"

    topic_id: Mapped[int] = mapped_column(ForeignKey("study_topics.id", ondelete="CASCADE"), primary_key=True)
    note_id: Mapped[int] = mapped_column(NoteId, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="unread")


class ReviewCard(Base):
    __tablename__ = "study_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(NoteId, ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(LongText)
    due: Mapped[date] = mapped_column(Date, index=True)
    wrong: Mapped[bool] = mapped_column(default=False)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=0)


class StarterBankInstall(Base):
    __tablename__ = "study_starter_installs"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
