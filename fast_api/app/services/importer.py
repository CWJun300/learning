"""把上传的文本文件解析成笔记。

支持：
- `.md` / `.txt` / 其他纯文本：支持极简 front matter（title / tags），
  没有 front matter 时用第一个一级标题当标题，再退化为文件名；
- `.json`：数组，或 `{"notes": [...]}`，或单个对象。

这里全是纯函数，方便单测；入库逻辑在 api/imports.py。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

MAX_TITLE_LEN = 200


@dataclass
class ParsedNote:
    title: str
    content: str = ""
    tags: list[str] = field(default_factory=list)


def _stem(filename: str) -> str:
    stem = Path(filename or "").stem
    return stem or filename or "未命名"


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """解析极简 front matter：只认 `key: value`，不引入 YAML 依赖。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta_lines = text[3:end]
    body = text[end + 4 :]
    meta: dict[str, str] = {}
    for line in meta_lines.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()
    return meta, body.lstrip("\r\n")


def _split_tags(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip("\"'") for item in raw.split(",") if item.strip()]


def _normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _split_tags(value)
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _extract_title(fallback: str, body: str) -> tuple[str, str]:
    """用第一个一级标题当标题，并从正文里去掉这行，避免和页面标题重复。"""
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            heading = line[2:].strip()
            if heading:
                rest = "\n".join(lines[index + 1 :]).lstrip("\r\n")
                return heading[:MAX_TITLE_LEN], rest
            break
    return fallback[:MAX_TITLE_LEN], body


def parse_markdown(filename: str, text: str) -> ParsedNote:
    meta, body = _parse_front_matter(text or "")
    stem = _stem(filename)

    title = (meta.get("title") or "").strip()
    tags = _split_tags(meta["tags"]) if meta.get("tags") else []

    if not title:
        title, body = _extract_title(stem, body)

    return ParsedNote(title=title[:MAX_TITLE_LEN], content=body.strip(), tags=tags)


def parse_json(filename: str, text: str) -> list[ParsedNote]:
    try:
        data = json.loads(text or "")
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败：{exc.msg}") from exc

    if isinstance(data, dict):
        items = data["notes"] if isinstance(data.get("notes"), list) else [data]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON 顶层必须是对象或数组")

    stem = _stem(filename)
    notes: list[ParsedNote] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip() or stem
        content = item.get("content") or item.get("body") or item.get("markdown") or ""
        notes.append(
            ParsedNote(
                title=title[:MAX_TITLE_LEN],
                content=str(content),
                tags=_normalize_tags(item.get("tags")),
            )
        )

    if not notes:
        raise ValueError("JSON 里没有可导入的笔记")
    return notes


def parse_any(filename: str, text: str) -> list[ParsedNote]:
    """按扩展名分派；未知扩展名一律当纯文本处理。"""
    if (filename or "").lower().endswith(".json"):
        return parse_json(filename, text)
    return [parse_markdown(filename, text)]
