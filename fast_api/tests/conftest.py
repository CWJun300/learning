"""pytest 全局配置。

分两层：
- 索引内核（tokenizer / index_store / ranker / query_parser / highlight）：
  纯 Python 逻辑，不依赖数据库，任何机器都能跑；
- 接口测试：依赖 MySQL 的 kb_test 库，MySQL 不可用时自动跳过。

接口测试的隔离方式：每个用例一个外层事务，用例结束后整体回滚，
所以不会污染 kb_test 里的数据，也不用反复建表。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_engine():
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    from app.config import settings

    engine = create_engine(
        settings.test_database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


@pytest.fixture(scope="session")
def engine():
    import app.models  # noqa: F401  必须先导入模型，否则 Base.metadata 里没有表
    from app.db import Base

    try:
        eng = _make_engine()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"MySQL 不可用，跳过接口测试：{exc}")

    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    """一个用例一个事务，结束回滚。

    join_transaction_mode="create_savepoint" 让接口里的 session.commit()
    只提交到 SAVEPOINT，外层 trans.rollback() 仍然能全部撤销。
    """
    from sqlalchemy.orm import sessionmaker

    conn = engine.connect()
    trans = conn.begin()
    session = sessionmaker(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def client(db):
    """不进入上下文管理器，因此不会触发 lifespan（避免读到 kb_db 的生产数据）。"""
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.services.index_manager import index_manager
    from main import app

    index_manager.rebuild([])
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        index_manager.rebuild([])
