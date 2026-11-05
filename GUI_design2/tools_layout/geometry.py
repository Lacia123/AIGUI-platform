"""把抽象布局树递归展开为可评分的几何区域。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .domain import Canvas, Card, CardNode, ContainerNode, LayoutNode, Rect


@dataclass(frozen=True)
class CardMetrics:
    min_width: float
    preferred_width: float
    base_height: float
    target_aspect: float | None = None
    min_height: float = 96.0


@dataclass(frozen=True)
class LayoutGeometry:
    card_rects: dict[int, Rect]
    container_rects: dict[ContainerNode, Rect]


def card_metrics(card: Card) -> CardMetrics:
    name = card.card_type.lower()
    if any(word in name for word in ("hero", "showcase", "banner")):
        return CardMetrics(320, 720, 300, 16 / 7, min_height=160.0)
    if any(word in name for word in ("chart", "plot", "graph", "image", "media")):
        return CardMetrics(280, 520, 280, 16 / 9, min_height=140.0)
    if any(word in name for word in ("table", "list", "article", "markdown")):
        return CardMetrics(300, 540, 180, min_height=120.0)
    if any(word in name for word in ("stat", "metric", "kpi", "target", "summary")):
        return CardMetrics(150, 220, 130, 3 / 2, min_height=72.0)
    if any(word in name for word in ("tag", "badge", "button")):
        return CardMetrics(100, 160, 90, min_height=48.0)
    return CardMetrics(200, 360, 150, min_height=96.0)


def estimated_content_height(card: Card, width: float) -> float:
    metrics = card_metrics(card)
    usable_width = max(80.0, width - 32.0)
    average_glyph_width = 9.0
    chars_per_line = max(8, int(usable_width / average_glyph_width))
    text_lines = math.ceil(card.char_count / chars_per_line)
    token_lines = math.ceil(card.token_count / max(6, int(chars_per_line * 0.65)))
    content_lines = max(text_lines, token_lines)
    return (
        metrics.base_height
        + max(0, content_lines - 2) * 20.0
        + card.element_count * 7.0
    )


def intrinsic_size(node: LayoutNode, cards: list[Card], gap: float) -> tuple[float, float]:
    if isinstance(node, CardNode):
        metrics = card_metrics(cards[node.card_index])
        return metrics.preferred_width, estimated_content_height(
            cards[node.card_index], metrics.preferred_width
        )

    sizes = [intrinsic_size(child, cards, gap) for child in node.children]
    if node.kind == "row":
        return (
            sum(width for width, _ in sizes) + gap * max(0, len(sizes) - 1),
            max(height for _, height in sizes),
        )
    return (
        max(width for width, _ in sizes),
        sum(height for _, height in sizes) + gap * max(0, len(sizes) - 1),
    )


def min_size(node: LayoutNode, cards: list[Card], gap: float) -> tuple[float, float]:
    """子树能接受的最小 (宽, 高)：行取宽和、高取最大；列反之。"""
    if isinstance(node, CardNode):
        metrics = card_metrics(cards[node.card_index])
        return metrics.min_width, metrics.min_height
    sizes = [min_size(child, cards, gap) for child in node.children]
    gaps = gap * max(0, len(sizes) - 1)
    if node.kind == "row":
        return sum(width for width, _ in sizes) + gaps, max(
            height for _, height in sizes
        )
    return max(width for width, _ in sizes), sum(
        height for _, height in sizes
    ) + gaps


def _allocate(
    total: float, weights: list[float], minimums: list[float] | None = None
) -> list[float]:
    """先给每项保底最小尺寸，剩余空间再按权重分配；保底总和超限时按比例压缩保底。"""
    if not weights:
        return []
    safe_total = max(0.0, total)
    mins = list(minimums) if minimums is not None else [0.0] * len(weights)
    min_total = sum(mins)
    if min_total >= safe_total:
        if min_total <= 0:
            return [safe_total / len(weights)] * len(weights)
        return [safe_total * value / min_total for value in mins]
    remaining = safe_total - min_total
    weight_sum = sum(max(weight, 1.0) for weight in weights)
    return [
        minimum + remaining * max(weight, 1.0) / weight_sum
        for minimum, weight in zip(mins, weights, strict=True)
    ]


def layout_geometry(
    root: ContainerNode,
    cards: list[Card],
    canvas: Canvas,
) -> LayoutGeometry:
    card_rects: dict[int, Rect] = {}
    container_rects: dict[ContainerNode, Rect] = {}

    def place(node: LayoutNode, rect: Rect) -> None:
        if isinstance(node, CardNode):
            card_rects[node.card_index] = rect
            return
        container_rects[node] = rect
        child_sizes = [intrinsic_size(child, cards, canvas.gap) for child in node.children]
        child_mins = [min_size(child, cards, canvas.gap) for child in node.children]
        gap_total = canvas.gap * max(0, len(node.children) - 1)

        if node.kind == "row":
            widths = _allocate(
                rect.width - gap_total,
                [width for width, _ in child_sizes],
                [width for width, _ in child_mins],
            )
            cursor = rect.x
            for child, width in zip(node.children, widths, strict=True):
                place(child, Rect(cursor, rect.y, width, rect.height))
                cursor += width + canvas.gap
        else:
            heights = _allocate(
                rect.height - gap_total,
                [height for _, height in child_sizes],
                [height for _, height in child_mins],
            )
            cursor = rect.y
            for child, height in zip(node.children, heights, strict=True):
                place(child, Rect(rect.x, cursor, rect.width, height))
                cursor += height + canvas.gap

    place(root, Rect(0.0, 0.0, canvas.width, canvas.height))
    return LayoutGeometry(card_rects, container_rects)


# 平台前端（grid_canvas 首页）按 228x216/16 把像素画布换算成格子，
# 只认 grid:CxR;(w,h,x,y,type)... 布局序列。见 grid_canvas/src/layoutFormat.ts。
_PLATFORM_CELL_W = 228.0
_PLATFORM_CELL_H = 216.0


def _distribute_cells(total: int, weights: list[float]) -> list[int]:
    """把 total 个格子按权重分给子节点，每项至少 1 格（最大余数法）。"""
    count = len(weights)
    if total < count:
        raise ValueError("格子数少于子节点数，无法量化")
    remaining = total - count
    weight_sum = sum(max(weight, 1.0) for weight in weights) or 1.0
    raw = [remaining * max(weight, 1.0) / weight_sum for weight in weights]
    added = [int(math.floor(value)) for value in raw]
    leftover = remaining - sum(added)
    order = sorted(range(count), key=lambda i: raw[i] - added[i], reverse=True)
    for index in order[:leftover]:
        added[index] += 1
    return [1 + value for value in added]


def grid_size_for_canvas(canvas: Canvas) -> tuple[int, int] | None:
    """像素画布能整除成平台格子时返回 (cols, rows)，否则 None。"""
    cols = round((canvas.width + canvas.gap) / (_PLATFORM_CELL_W + canvas.gap))
    rows = round((canvas.height + canvas.gap) / (_PLATFORM_CELL_H + canvas.gap))
    if cols < 1 or rows < 1:
        return None
    if abs(cols * _PLATFORM_CELL_W + (cols - 1) * canvas.gap - canvas.width) > 1.0:
        return None
    if abs(rows * _PLATFORM_CELL_H + (rows - 1) * canvas.gap - canvas.height) > 1.0:
        return None
    return cols, rows


def tree_to_grid_sequence(
    root: ContainerNode,
    cards: list[Card],
    canvas: Canvas,
) -> str | None:
    """把布局树量化为前端布局序列；画布对不上平台格子时返回 None。

    子节点按固有尺寸权重切分所在矩形（整格、至少 1 格），结果必然
    铺满、不重叠、不越界，可直接粘贴到前端首页渲染。
    """
    grid = grid_size_for_canvas(canvas)
    if grid is None:
        return None
    cols, rows = grid
    boxes: dict[int, tuple[int, int, int, int]] = {}

    def alloc(node: LayoutNode, x: int, y: int, width: int, height: int) -> None:
        if isinstance(node, CardNode):
            boxes[node.card_index] = (width, height, x, y)
            return
        sizes = [intrinsic_size(child, cards, canvas.gap) for child in node.children]
        if node.kind == "row":
            parts = _distribute_cells(width, [size[0] for size in sizes])
            cursor = x
            for child, part in zip(node.children, parts, strict=True):
                alloc(child, cursor, y, part, height)
                cursor += part
        else:
            parts = _distribute_cells(height, [size[1] for size in sizes])
            cursor = y
            for child, part in zip(node.children, parts, strict=True):
                alloc(child, x, cursor, width, part)
                cursor += part

    try:
        alloc(root, 0, 0, cols, rows)
    except ValueError:
        return None
    ordered = sorted(boxes.items(), key=lambda item: (item[1][3], item[1][2]))
    body = "".join(
        f"({width},{height},{x},{y},{cards[index].card_type})"
        for index, (width, height, x, y) in ordered
    )
    return f"grid:{cols}x{rows};{body}"
