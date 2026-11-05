"""可解释的布局质量评分；分数越低越好。"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .domain import Canvas, Card, CardNode, ContainerNode, LayoutNode
from .geometry import card_metrics, estimated_content_height, layout_geometry


@dataclass(frozen=True)
class ScoreWeights:
    overflow: float = 12.0
    too_narrow: float = 10.0
    aspect_ratio: float = 1.8
    excess_space: float = 0.8
    complexity: float = 0.7
    depth: float = 1.2
    row_mismatch: float = 2.5
    mobile_row_root: float = 2.0
    header: float = 2.0
    type_group: float = 2.5
    thin_banner: float = 2.0


# 横排受损的是长文本/表格类；hero/showcase 横排是画廊与侧栏，不在此列。
_FULL_WIDTH_HINTS = (
    "table",
    "list",
    "article",
    "markdown",
    "dashboard",
)


def _tree_penalties(root: ContainerNode, cards: list[Card]) -> dict[str, float]:
    containers = 0
    max_depth = 1
    row_mismatch = 0.0

    def visit(node: LayoutNode, depth: int) -> None:
        nonlocal containers, max_depth, row_mismatch
        if isinstance(node, CardNode):
            return
        containers += 1
        max_depth = max(max_depth, depth)
        if node.kind == "row":
            for child in node.children:
                if isinstance(child, CardNode):
                    card = cards[child.card_index]
                    name = card.card_type.lower()
                    if any(hint in name for hint in _FULL_WIDTH_HINTS):
                        row_mismatch += 1.0
                    elif card.char_count > 320:
                        row_mismatch += min(2.0, card.char_count / 320.0)
        for child in node.children:
            visit(child, depth + 1)

    visit(root, 1)
    count = max(1, len(cards))
    return {
        "complexity": max(0.0, (containers - 1) / count),
        "depth": max(0.0, max_depth - 3) ** 2,
        "row_mismatch": row_mismatch / count,
    }


def _parent_map(root: ContainerNode) -> dict[int, ContainerNode]:
    parents: dict[int, ContainerNode] = {}

    def visit(node: ContainerNode) -> None:
        for child in node.children:
            if isinstance(child, CardNode):
                parents[child.card_index] = node
            else:
                visit(child)

    visit(root)
    return parents


def _type_group_penalty(root: ContainerNode, cards: list[Card]) -> float:
    """连续同类卡应尽量成为同一容器的直接子节点（指标成行、错题成叠、画廊成排）。"""
    if len(cards) < 2:
        return 0.0
    parents = _parent_map(root)
    pairs = 0
    grouped = 0
    for left, right in zip(cards, cards[1:]):
        if left.card_type != right.card_type:
            continue
        pairs += 1
        if parents.get(left.index) is parents.get(right.index):
            grouped += 1
    if pairs == 0:
        return 0.0
    return 1.0 - grouped / float(pairs)


def score_tree(
    root: ContainerNode,
    cards: list[Card],
    canvas: Canvas,
    weights: ScoreWeights = ScoreWeights(),
) -> tuple[float, dict[str, float]]:
    """返回总分和各项已加权惩罚。"""
    geometry = layout_geometry(root, cards, canvas)
    raw = {
        "overflow": 0.0,
        "too_narrow": 0.0,
        "aspect_ratio": 0.0,
        "excess_space": 0.0,
        "header": 0.0,
        "type_group": _type_group_penalty(root, cards),
        "thin_banner": 0.0,
        **_tree_penalties(root, cards),
        "mobile_row_root": float(root.kind == "row" and canvas.width < 600),
    }
    # 队首 textCard 应通栏；非队首的 text 不套这条。
    if cards and cards[0].card_type == "textCard":
        first = geometry.card_rects[cards[0].index]
        if canvas.width > 0 and first.width < 0.95 * canvas.width:
            raw["header"] = 1.0 - first.width / canvas.width
    # 非标题/指标的大卡被压成通栏细条时罚分（通栏叠条的主要形态）。
    thin_count = 0
    for card in cards:
        name = card.card_type.lower()
        if card.card_type == "textCard" or "stat" in name or "target" in name:
            continue
        rect = geometry.card_rects[card.index]
        if (
            canvas.width > 0
            and canvas.height > 0
            and rect.width > 0.8 * canvas.width
            and rect.height < 0.12 * canvas.height
        ):
            thin_count += 1
    raw["thin_banner"] = thin_count / float(max(1, len(cards)))

    for card in cards:
        rect = geometry.card_rects[card.index]
        metrics = card_metrics(card)
        needed_height = estimated_content_height(card, rect.width)
        if rect.height < needed_height:
            raw["overflow"] += ((needed_height - rect.height) / needed_height) ** 2
        if rect.width < metrics.min_width:
            raw["too_narrow"] += (
                (metrics.min_width - rect.width) / metrics.min_width
            ) ** 2
        if metrics.target_aspect is not None and rect.height > 0:
            actual_aspect = max(0.05, rect.width / rect.height)
            raw["aspect_ratio"] += math.log(
                actual_aspect / metrics.target_aspect
            ) ** 2
        if rect.height > needed_height * 2.5:
            raw["excess_space"] += (
                (rect.height - needed_height * 2.5) / rect.height
            ) ** 2

    count = max(1, len(cards))
    for name in ("overflow", "too_narrow", "aspect_ratio", "excess_space"):
        raw[name] /= count

    weighted = {
        name: raw[name] * getattr(weights, name)
        for name in raw
    }
    return sum(weighted.values()), weighted
