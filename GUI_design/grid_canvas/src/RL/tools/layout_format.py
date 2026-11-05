"""布局序列格式：可选画布头 + 单卡 (w,h,x,y) 或 (w,h,x,y,\"type\")。

可渲染示例（整段粘贴到页面「模型输出序列」）:
  grid:13x8;(13,1,0,0,"textCard")(3,2,0,1,"targetStatCard")
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

# 可选画布头：grid:13x8; 或 grid:13×8
GRID_HEADER_RE = re.compile(
    r"^\s*grid\s*:\s*(\d+)\s*[x×X]\s*(\d+)\s*;?\s*",
    re.IGNORECASE,
)

# 第 5 段可选：双引号 / 单引号 / 无引号标识符
CARD_RE = re.compile(
    r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)"
    r'(?:\s*,\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,)]+)))?\s*\)'
)


@dataclass(frozen=True)
class LayoutCard:
    """单卡描述：(w, h, x, y[, type])。"""

    w: int
    h: int
    x: int
    y: int
    type: Optional[str] = None

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.w, self.h, self.x, self.y)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseLayoutResult:
    cards: list[LayoutCard]
    grid_cols: Optional[int] = None
    grid_rows: Optional[int] = None


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


def split_grid_header(text: str) -> tuple[Optional[tuple[int, int]], str]:
    """拆出可选 grid:CxR 头，返回 ((cols,rows)|None, 剩余正文)。"""
    raw = text.strip()
    m = GRID_HEADER_RE.match(raw)
    if not m:
        return None, raw
    return (int(m.group(1)), int(m.group(2))), raw[m.end() :]


def parse_layout_sequence(
    text: str,
    *,
    cols: Optional[int] = None,
    rows: Optional[int] = None,
    check_overlap: bool = True,
) -> ParseLayoutResult:
    """
    解析布局序列。

    可选头：`grid:13x8;`
    单卡：`(w,h,x,y)` 或 `(w,h,x,y,"type")`
    """
    raw = text.strip()
    if not raw:
        return ParseLayoutResult(cards=[])

    grid, body = split_grid_header(raw)
    grid_cols = grid[0] if grid else None
    grid_rows = grid[1] if grid else None
    # 显式传入的 cols/rows 优先用于越界校验
    check_cols = cols if cols is not None else grid_cols
    check_rows = rows if rows is not None else grid_rows

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
        type_ = match.group(5) or match.group(6) or match.group(7) or None
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
        card = LayoutCard(w=w, h=h, x=x, y=y, type=type_)
        if (
            check_cols is not None
            and check_rows is not None
            and not _in_bounds(card, check_cols, check_rows)
        ):
            raise LayoutFormatError(
                f"card {token} out of bounds on {check_cols}×{check_rows} grid",
                index=index,
                raw=token,
            )
        cards.append(card)

    if not cards:
        raise LayoutFormatError(
            'no cards found; expected tokens like (w,h,x,y) or (w,h,x,y,"type")',
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

    return ParseLayoutResult(
        cards=cards,
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    )


def sort_cards_reading_order(cards: list) -> list:
    """阅读序：自上而下逐行，同行自左而右（与放置先后无关）。"""

    def key(c) -> tuple[int, int]:
        if isinstance(c, LayoutCard):
            return (c.y, c.x)
        if isinstance(c, dict):
            return (int(c["y"]), int(c["x"]))
        # tuple (w,h,x,y) or (w,h,x,y,type)
        return (int(c[3]), int(c[2]))

    return sorted(cards, key=key)


def _format_one(w: int, h: int, x: int, y: int, type_: str | None = None) -> str:
    if not type_:
        return f"({w},{h},{x},{y})"
    t = str(type_)
    # 无空格/逗号/括号/引号时不加引号，便于从 JSON 原样复制
    if re.fullmatch(r"[^\s,()\"']+", t):
        return f"({w},{h},{x},{y},{t})"
    esc = t.replace("\\", "\\\\").replace('"', '\\"')
    return f'({w},{h},{x},{y},"{esc}")'


def stringify_layout_sequence(
    cards: Iterable[
        LayoutCard
        | tuple[int, int, int, int]
        | tuple[int, int, int, int, str | None]
    ],
    *,
    style: str = "compact",
    cols: int | None = None,
    rows: int | None = None,
) -> str:
    """序列化。cols/rows 给定时加 `grid:CxR;` 头，可供页面直接渲染。

    卡片顺序固定为阅读序（先 y 后 x）。
    """
    ordered = sort_cards_reading_order(list(cards))
    parts: list[str] = []
    for c in ordered:
        if isinstance(c, LayoutCard):
            parts.append(_format_one(c.w, c.h, c.x, c.y, c.type))
        elif len(c) >= 5:
            parts.append(_format_one(int(c[0]), int(c[1]), int(c[2]), int(c[3]), c[4]))
        else:
            parts.append(_format_one(int(c[0]), int(c[1]), int(c[2]), int(c[3])))
    if style == "list":
        body = "[" + ", ".join(parts) + "]"
    else:
        body = "".join(parts)
    if cols is not None and rows is not None:
        return f"grid:{int(cols)}x{int(rows)};{body}"
    return body
