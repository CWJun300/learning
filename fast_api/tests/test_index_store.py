"""InvertedIndex 行为约定（先于实现编写）。"""

from pathlib import Path
from uuid import uuid4

import pytest

from app.services.index_store import IndexLoadError, InvertedIndex

# 持久化用例的文件落在项目内的 _files 目录，避免依赖系统临时目录
FILES_DIR = Path(__file__).resolve().parent / "_files"


@pytest.fixture
def index_file():
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    path = FILES_DIR / f"index_{uuid4().hex}.json"
    yield path
    if path.exists():
        path.unlink()


def make_index() -> InvertedIndex:
    idx = InvertedIndex()
    idx.add(1, "苹果 香蕉")
    idx.add(2, "苹果 苹果 橙子")
    idx.add(3, "西瓜")
    return idx


class TestAddAndQuery:
    def test_new_doc_can_be_found(self):
        idx = InvertedIndex()
        idx.add(1, "苹果")
        postings = idx.postings("苹果")
        assert [(p.doc_id, p.tf) for p in postings] == [(1, 1)]

    def test_term_frequency_is_counted(self):
        postings = make_index().postings("苹果")
        assert {p.doc_id: p.tf for p in postings} == {1: 1, 2: 2}

    def test_unknown_term_returns_empty(self):
        assert make_index().postings("不存在的词") == []

    def test_doc_count(self):
        assert make_index().doc_count() == 3

    def test_doc_length(self):
        idx = make_index()
        assert idx.doc_length(2) == 3  # 苹果 苹果 橙子
        assert idx.doc_length(3) == 1

    def test_terms_of_doc(self):
        assert make_index().doc_terms(1) == {"苹果", "香蕉"}

    def test_add_same_doc_twice_does_not_double_count(self):
        idx = InvertedIndex()
        idx.add(1, "苹果")
        idx.add(1, "苹果")
        assert idx.postings("苹果")[0].tf == 1
        assert idx.doc_count() == 1


class TestRemoveAndUpdate:
    def test_removed_doc_disappears(self):
        idx = make_index()
        idx.remove(1)
        assert [p.doc_id for p in idx.postings("苹果")] == [2]
        assert idx.doc_count() == 2

    def test_remove_keeps_other_terms_intact(self):
        idx = make_index()
        idx.remove(1)
        assert [p.doc_id for p in idx.postings("西瓜")] == [3]

    def test_remove_unknown_doc_is_noop(self):
        idx = make_index()
        idx.remove(999)
        assert idx.doc_count() == 3

    def test_update_removes_old_terms(self):
        idx = make_index()
        idx.update(1, "香蕉")
        assert 1 not in [p.doc_id for p in idx.postings("苹果")]
        assert [p.doc_id for p in idx.postings("香蕉")] == [1]

    def test_update_adds_new_terms(self):
        idx = make_index()
        idx.update(3, "西瓜 葡萄")
        assert idx.doc_terms(3) == {"西瓜", "葡萄"}


class TestPersistence:
    def test_save_then_load_roundtrip(self, index_file):
        idx = make_index()
        idx.save(index_file)

        loaded = InvertedIndex.load(index_file)
        assert loaded.doc_count() == idx.doc_count()
        assert {p.doc_id: p.tf for p in loaded.postings("苹果")} == {1: 1, 2: 2}
        assert loaded.doc_length(2) == 3
        assert loaded.doc_terms(3) == {"西瓜"}

    def test_load_missing_file_raises(self, index_file):
        with pytest.raises(IndexLoadError):
            InvertedIndex.load(index_file)

    def test_load_corrupted_file_raises(self, index_file):
        index_file.write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(IndexLoadError):
            InvertedIndex.load(index_file)

    def test_load_empty_index_file(self, index_file):
        idx = InvertedIndex()
        idx.save(index_file)
        loaded = InvertedIndex.load(index_file)
        assert loaded.doc_count() == 0
        assert loaded.postings("苹果") == []
