"""查询语法解析。

支持：
    普通词        -> should（可选命中，参与打分）
    +词           -> must  （必须命中）
    "完整短语"     -> phrases（要求原文包含该短语）
    #标签         -> tags

未闭合的引号不会报错，里面的内容按普通词处理。
"""

import re
from dataclasses import dataclass, field

_CLOSED_QUOTE = re.compile(r'"([^"]*)"')


@dataclass
class ParsedQuery:
    must: list[str] = field(default_factory=list)
    should: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.must or self.should or self.phrases or self.tags)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_query(raw: str) -> ParsedQuery:
    query = ParsedQuery()
    if not raw or not raw.strip():
        return query

    text = raw
    # 1) 先摘出成对的引号短语
    for match in _CLOSED_QUOTE.finditer(text):
        phrase = match.group(1).strip()
        if phrase:
            query.phrases.append(phrase)
    text = _CLOSED_QUOTE.sub(" ", text)

    # 2) 残留的引号（未闭合）直接去掉，内容按普通词处理
    text = text.replace('"', " ")

    # 3) 逐词分类
    for token in text.split():
        if token.startswith("#"):
            tag = token[1:].strip()
            if tag:
                query.tags.append(tag)
        elif token.startswith("+"):
            word = token[1:].strip()
            if word:
                query.must.append(word)
        else:
            word = token.strip()
            if word:
                query.should.append(word)

    query.must = _dedupe(query.must)
    query.should = _dedupe(query.should)
    query.phrases = _dedupe(query.phrases)
    query.tags = _dedupe(query.tags)
    return query
