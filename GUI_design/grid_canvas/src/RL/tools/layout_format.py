"""布局序列格式解析：单卡 (w,h,x,y)。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

CARD_RE = re.compile(
    r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)"
)


@dataclass(frozen=True)
class LayoutCard:
    """单卡描述：(w, h, x, y)。"""

    w: int
    h: int
    x: int
    y: int

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.w, self.h, self.x, self.y)

    def to_dict(self) -> dict:
        return asdict(self)


class LayoutFormatError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        index: Optional[int] = None,
        raw: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.index = index
        self.raw = raw


def _overlap(a: LayoutCard, b: LayoutCard) -> bool:
    return not (
        a.x + a.w <= b.x
        or b.x + b.w <= a.x
        or a.y + a.h <= b.y
        or b.y + b.h <= a.y
    )


def _in_bounds(card: LayoutCard, cols: int, rows: int) -> bool:
    return (
        card.x >= 0
        and card.y >= 0
        and card.w > 0
        and card.h > 0
        and card.x + card.w <= cols
        and card.y + card.h <= rows
    )


def parse_layout_sequence(
    text: str,
    *,
    cols: Optional[int] = None,
    rows: Optional[int] = None,
    check_overlap: bool = True,
) -> list[LayoutCard]:
    """
    解析布局序列。

    单卡格式：`(w,h,x,y)`
    序列示例：
    - `(2,1,0,0)(3,2,2,0)`
    - `[(2,1,0,0), (3,2,2,0)]`
    """
    raw = text.strip()
    if not raw:
        return []

    body = raw
    if body.startswith("["):
        body = body[1:]
    if body.endswith("]"):
        body = body[:-1]

    residual = CARD_RE.sub("", body)
    residual = re.sub(r"[\s,;|]+", "", residual)
    if residual:
        raise LayoutFormatError(
            f'invalid layout sequence: unexpected token near "{residual[:24]}"',
            raw=text,
        )

    cards: list[LayoutCard] = []
    for index, match in enumerate(CARD_RE.finditer(body)):
        w, h, x, y = (int(match.group(i)) for i in range(1, 5))
        token = match.group(0)
        if w <= 0 or h <= 0:
            raise LayoutFormatError(
                f"w and h must be positive in {token}",
                index=index,
                raw=token,
            )
        if x < 0 or y < 0:
            raise LayoutFormatError(
                f"x and y must be >= 0 in {token}",
                index=index,
                raw=token,
            )
        card = LayoutCard(w=w, h=h, x=x, y=y)
        if cols is not None and rows is not None and not _in_bounds(card, cols, rows):
            raise LayoutFormatError(
                f"card {token} out of bounds on {cols}×{rows} grid",
                index=index,
                raw=token,
            )
        cards.append(card)

    if not cards:
        raise LayoutFormatError(
            "no cards found; expected tokens like (w,h,x,y)",
            raw=text,
        )

    if check_overlap:
        for i, a in enumerate(cards):
            for j in range(i + 1, len(cards)):
                b = cards[j]
                if _overlap(a, b):
                    raise LayoutFormatError(
                        f"overlap between card#{i} {a.to_tuple()} and card#{j} {b.to_tuple()}",
                        index=i,
                    )

    return cards


def stringify_layout_sequence(
    cards: Iterable[LayoutCard | tuple[int, int, int, int]],
    *,
    style: str = "compact",
) -> str:
    """序列化。style='compact' -> (w,h,x,y)(w,h,x,y)；'list' -> [(w,h,x,y), ...]。"""
    parts: list[str] = []
    for c in cards:
        if isinstance(c, LayoutCard):
            w, h, x, y = c.w, c.h, c.x, c.y
        else:
            w, h, x, y = c
        parts.append(f"({w},{h},{x},{y})")
    if style == "list":
        return "[" + ", ".join(parts) + "]"
    return "".join(parts)
