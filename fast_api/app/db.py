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
    )#配置engine对象


engine = _build_engine(settings.database_url)#engine是管理sql连接池的对象

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)#配置session对象


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:#以迭代器返回
    """FastAPI 依赖：每个请求一个会话，用完必关。"""
    db = SessionLocal()
    try:
        yield db#交出去一个session对象，session是封装好的能够向engines索要connect并处理的对象，yield意为返回完值才执行后面步骤，若还有yield可继续返回值
    finally:
        db.close()
