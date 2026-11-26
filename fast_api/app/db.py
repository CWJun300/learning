"""数据库引擎与会话。

要点：
- MySQL：pool_pre_ping 探活、pool_recycle 定期回收，避免 stale connection；
- SQLite：不支持 pool_size 等参数，改为：
    * 关闭 pysqlite 的隐式 BEGIN，由 begin 事件显式发 BEGIN
      （否则 SAVEPOINT 与驱动事务处理冲突，测试用例之间会串数据）
    * PRAGMA foreign_keys=ON → 让 ON DELETE CASCADE 真正生效（SQLite 默认关）
    * PRAGMA journal_mode=WAL + busy_timeout → 减少 "database is locked"
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _build_engine(url: str, poolclass=None):
    """创建引擎。poolclass 用于测试（NullPool，避免跨用例复用连接）。"""
    is_sqlite = url.startswith("sqlite")

    kwargs = {"future": True}
    if poolclass is not None:
        kwargs["poolclass"] = poolclass

    if is_sqlite:
        kwargs["connect_args"] = {
            # FastAPI 的同步路由跑在线程池里，连接会跨线程使用
            "check_same_thread": False,
            "timeout": 30,
            # 关键：关掉 pysqlite 的隐式 BEGIN，改由 begin 事件显式开启
            "isolation_level": None,
        }
    elif poolclass is None:
        kwargs.update(
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    engine = create_engine(url, **kwargs)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=30000")
                # 内存库不支持 WAL，失败也无所谓
                cursor.execute("PRAGMA journal_mode=WAL")
            finally:
                cursor.close()

        @event.listens_for(engine, "begin")
        def _sqlite_begin(conn):
            conn.exec_driver_sql("BEGIN")

    return engine


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
