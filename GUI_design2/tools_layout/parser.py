"""Card-only PSUIP 解析与轻量特征提取。"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .domain import Card


_TAG_RE = re.compile(r"<[^>]+>")
_XML_TOKEN_RE = re.compile(
    r"<\s*(/?)\s*([A-Za-z_][\w:.-]*)(?:\s[^<>]*?)?\s*(/?)>"
)
_TABLE_RE = re.compile(r"\[table:([^\]]+)\]")
_TOKEN_RE = re.compile(
    r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:['.-][A-Za-z0-9]+)*|[^\w\s]",
    re.UNICODE,
)
_TOP_LEVEL_TAG_RE = re.compile(
    r"(?m)^[ \t]*<([A-Za-z_][\w:.-]*)(?:\s[^<>]*?)?>"
)


def _features(index: int, card_type: str, psuip: str) -> Card:
    text = html.unescape(_TAG_RE.sub(" ", psuip))
    text = " ".join(text.split())
    openings = [
        match
        for match in _XML_TOKEN_RE.finditer(psuip)
        if not match.group(1) and not match.group(3)
    ]
    element_count = max(0, len(openings) - (not card_type.startswith("[table:")))
    return Card(
        index=index,
        card_type=card_type,
        psuip=psuip,
        char_count=len(text),
        token_count=len(_TOKEN_RE.findall(text)),
        element_count=element_count,
    )


def _xml_card_end(source: str, start: int) -> tuple[str, int]:
    first = _XML_TOKEN_RE.match(source, start)
    if first is None or first.group(1):
        raise ValueError(f"位置 {start} 不是 Card 开始标签")
    card_type = first.group(2)
    if first.group(3):
        return card_type, first.end()

    stack = [card_type]
    for match in _XML_TOKEN_RE.finditer(source, first.end()):
        closing, tag, self_closing = match.groups()
        if closing:
            if not stack or stack[-1] != tag:
                expected = stack[-1] if stack else "无"
                raise ValueError(f"标签 </{tag}> 与当前 <{expected}> 不匹配")
            stack.pop()
            if not stack:
                return card_type, match.end()
        elif not self_closing:
            stack.append(tag)
    raise ValueError(f"Card <{card_type}> 缺少结束标签")


def parse_cards(source: str, source_name: str = "<memory>") -> list[Card]:
    """解析连续排列的顶层 Card，并保留每张 Card 的原始文本。"""
    raw_cards: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(source):
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor >= len(source):
            break

        table = _TABLE_RE.match(source, cursor)
        if table:
            next_tag = _TOP_LEVEL_TAG_RE.search(source, table.end())
            end = len(source) if next_tag is None else next_tag.start()
            raw_cards.append(
                (f"[table:{table.group(1)}]", source[cursor:end].strip())
            )
            cursor = end
            continue

        try:
            card_type, end = _xml_card_end(source, cursor)
        except ValueError as error:
            raise ValueError(f"{source_name}: {error}") from error
        raw_cards.append((card_type, source[cursor:end]))
        cursor = end

    if not raw_cards:
        raise ValueError(f"{source_name}: 没有找到 Card")
    return [
        _features(index, card_type, psuip)
        for index, (card_type, psuip) in enumerate(raw_cards)
    ]


def parse_card_file(path: str | Path) -> list[Card]:
    card_path = Path(path)
    return parse_cards(card_path.read_text(encoding="utf-8"), card_path.name)
