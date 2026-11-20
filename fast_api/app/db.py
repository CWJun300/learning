"""数据库引擎与会话。

要点：
- pool_pre_ping：MySQL 会踢掉空闲连接，取连接前先探活；
- pool_recycle：每小时回收一次，避免 stale connection；
- SQLite 不支持 pool_size/max_overflow，做兼容处理（应急预案用）。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )


engine = _build_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个会话，用完必关。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
