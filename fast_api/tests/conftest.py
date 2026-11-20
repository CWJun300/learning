"""pytest 全局配置。

约定：
- 索引内核（tokenizer / index_store / ranker / query_parser / highlight）
  是纯 Python 逻辑，不依赖数据库，任何机器都能跑。
- 接口测试需要 MySQL，标记为 db，MySQL 不可用时自动跳过。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def mysql_available() -> bool:
    """探测 MySQL 是否可用，供接口测试跳过用。"""
    try:
        from app.config import settings
        from sqlalchemy import create_engine, text
    except Exception:
        return False

    try:
        engine = create_engine(settings.test_database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False
