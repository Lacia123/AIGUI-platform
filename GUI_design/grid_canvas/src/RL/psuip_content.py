"""从 gird_with_cardtype 源稿切出每张卡的裸 PSUIP，供 layout-check 使用。"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import psuip_source_dir

CARD_TAGS = (
    "targetStatCard",
    "mistakesCard",
    "showcaseCard",
    "summaryCard",
    "textCard",
    "commonStyleServiceListDesc",
    "pairedImageTextCard",
    "heroCard",
    "contentSummaryCard",
    "Topology",
)

_TAG_RE = re.compile(r"<(/)?([A-Za-z_:][\w:.-]*)([^>]*)>", re.DOTALL)
_LAYOUT_PREFIXES = ("layout:", "grid:")


def _is_layout_tag(name: str) -> bool:
    return name.startswith(_LAYOUT_PREFIXES)


def _skip_comment(src: str, pos: int) -> int:
    end = src.find("-->", pos)
    return len(src) if end < 0 else end + 3


def _element_end(src: str, start: int, tag: str) -> int:
    """返回包含开闭标签的元素结束下标（不含之后的文本）。"""
    pos = start
    depth = 0
    while pos < len(src):
        if src.startswith("<!--", pos):
            pos = _skip_comment(src, pos)
            continue
        m = _TAG_RE.search(src, pos)
        if not m:
            return len(src)
        name = m.group(2)
        closing = bool(m.group(1))
        self_close = m.group(3).rstrip().endswith("/")
        if name != tag:
            pos = m.end()
            continue
        if closing:
            depth -= 1
            pos = m.end()
            if depth <= 0:
                return pos
            continue
        if self_close:
            pos = m.end()
            if depth == 0:
                return pos
            continue
        depth += 1
        pos = m.end()
    return len(src)


def extract_snippets(src: str) -> list[dict[str, str]]:
    """按文档顺序切出卡片块；夹在卡片之间的正文记为 __rawMarkdown__。"""
    snippets: list[dict[str, str]] = []
    raw_parts: list[str] = []
    pos = 0
    n = len(src)

    def flush_raw() -> None:
        text = "".join(raw_parts).strip()
        raw_parts.clear()
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 8:
            return
        snippets.append({"type": "__rawMarkdown__", "psuip": text})

    while pos < n:
        if src.startswith("<!--", pos):
            pos = _skip_comment(src, pos)
            continue
        if src[pos] != "<":
            nxt = src.find("<", pos)
            raw_parts.append(src[pos:] if nxt < 0 else src[pos:nxt])
            pos = n if nxt < 0 else nxt
            continue
        m = _TAG_RE.match(src, pos)
        if not m:
            raw_parts.append(src[pos])
            pos += 1
            continue
        name = m.group(2)
        closing = bool(m.group(1))
        if name in CARD_TAGS and not closing:
            flush_raw()
            end = _element_end(src, pos, name)
            snippets.append({"type": name, "psuip": src[pos:end].strip()})
            pos = end
            continue
        if _is_layout_tag(name):
            pos = m.end()
            continue
        raw_parts.append(src[pos : m.end()])
        pos = m.end()

    flush_raw()
    return snippets


@lru_cache(maxsize=32)
def snippets_from_file(source_file: str) -> tuple[dict[str, str], ...]:
    path = psuip_source_dir() / source_file
    if not path.is_file():
        return ()
    return tuple(extract_snippets(path.read_text(encoding="utf-8")))


def _snippet_score(snippet: dict[str, str], type_: str, label: str) -> int:
    if snippet["type"] != type_:
        return -1
    if label and label.lower() in snippet["psuip"].lower():
        return 2
    return 1


def attach_psuip(
    cards: list[dict[str, Any]],
    *,
    source_file: str | None,
) -> None:
    """原地为队列中的卡补 type / psuip。已有 psuip 的卡不覆盖。"""
    if not source_file:
        return
    unused = [dict(s) for s in snippets_from_file(source_file)]
    for card in cards:
        if card.get("psuip"):
            continue
        type_ = str(card.get("type") or "")
        label = str(card.get("label") or "")
        if not type_:
            continue
        best_i = -1
        best_score = 0
        for i, snip in enumerate(unused):
            score = _snippet_score(snip, type_, label)
            if score > best_score:
                best_score = score
                best_i = i
        if best_i < 0:
            continue
        card["psuip"] = unused.pop(best_i)["psuip"]
