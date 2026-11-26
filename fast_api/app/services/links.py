"""从正文的 Markdown 链接提取稳定的笔记 ID，忽略代码示例和外部链接。"""

import re

from markdown_it import MarkdownIt

markdown = MarkdownIt("commonmark")
note_url = re.compile(r"/notes/([1-9][0-9]{0,18})")


def linked_note_ids(content: str) -> set[int]:
    ids = set()
    for block in markdown.parse(content):
        for token in block.children or ():
            if token.type == "link_open":
                match = note_url.fullmatch(token.attrGet("href") or "")
                if match and int(match[1]) <= 2**63 - 1:
                    ids.add(int(match[1]))
    return ids
