"""Pydantic v2 请求 / 响应模型。"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = ""
    tags: list[str] = Field(default_factory=list)


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = Field(default_factory=list)


class TagCount(BaseModel):
    name: str
    count: int


class SearchHit(BaseModel):
    id: int
    title: str
    snippet: str
    score: float
    tags: list[str] = Field(default_factory=list)


class PageOut(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: list[T]


class StatsOut(BaseModel):
    note_count: int
    term_count: int
    avg_note_length: float


class ErrorOut(BaseModel):
    code: int
    message: str
