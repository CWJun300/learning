"""索引管理器：持有内存中的倒排索引，并负责与数据库保持一致。

为什么要有这一层：
- 索引是"进程内状态"，数据库是"持久真相"，两者需要同步；
- 用 RLock 保护，因为同步 ORM 端点跑在线程池里，存在并发访问。
"""

import threading
from pathlib import Path

from app.config import settings
from app.services.index_store import IndexLoadError, InvertedIndex
from app.services.tokenizer import Tokenizer


class IndexManager:
    def __init__(self, index_path: str | Path | None = None, tokenizer: Tokenizer | None = None):
        self._lock = threading.RLock()
        self._path = Path(index_path or settings.index_path)
        self._tokenizer = tokenizer or Tokenizer()
        self._index = InvertedIndex()

    @property
    def index(self) -> InvertedIndex:
        return self._index

    @property
    def tokenizer(self) -> Tokenizer:
        return self._tokenizer

    # ---------- 持久化 ----------
    def load(self) -> InvertedIndex:
        with self._lock:
            try:
                self._index = InvertedIndex.load(self._path)
            except IndexLoadError:
                self._index = InvertedIndex()
            return self._index

    def save(self) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._index.save(self._path)

    # ---------- 增删改 ----------
    def add_note(self, note_id: int, text: str) -> None:
        with self._lock:
            self._index.add(note_id, text)

    def update_note(self, note_id: int, text: str) -> None:
        with self._lock:
            self._index.update(note_id, text)

    def remove_note(self, note_id: int) -> None:
        with self._lock:
            self._index.remove(note_id)

    def rebuild(self, items: list[tuple[int, str]]) -> None:
        """从数据库全量重建索引。items = [(note_id, 参与检索的文本)]"""
        with self._lock:
            fresh = InvertedIndex()
            for note_id, text in items:
                fresh.add(note_id, text)
            self._index = fresh


index_manager = IndexManager()
