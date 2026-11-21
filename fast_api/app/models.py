"""ORM 模型：notes / tags / note_tags。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# 笔记正文用 MEDIUMTEXT（最大 16MB），其他数据库退回普通 TEXT
LongText = Text().with_variant(MEDIUMTEXT(), "mysql")

note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", BigInteger, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    notes: Mapped[list[Note]] = relationship(
        secondary=note_tags,
        back_populates="tags",
    )
