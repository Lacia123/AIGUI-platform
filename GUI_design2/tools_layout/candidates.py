"""保持 Card 顺序的 row/column 候选树生成器。"""

from __future__ import annotations

from functools import lru_cache
from itertools import islice, product

from .domain import (
    Canvas,
    Card,
    CardNode,
    ContainerNode,
    LayoutKind,
    LayoutNode,
    canonical_key,
    validate_tree,
)


# 横排会明显受损的类型：长文本/表格类。hero/showcase 进横排是画廊与侧栏的
# 正常形态，不能在代理分里重罚，否则人工树在最终评分前就被剪掉。
_ROW_AVERSE_HINTS = (
    "table",
    "list",
    "article",
    "markdown",
    "dashboard",
)
_COMPACT_HINTS = ("stat", "metric", "kpi", "summary", "target", "tag", "badge")


def _opposite(kind: LayoutKind) -> LayoutKind:
    return "column" if kind == "row" else "row"


def _compositions(
    start: int,
    stop: int,
    max_parts: int | None = None,
) -> list[tuple[tuple[int, int], ...]]:
    """返回连续区间的所有切分，排除不切分的情况。"""
    length = stop - start
    result: list[tuple[tuple[int, int], ...]] = []
    for mask in range(1, 1 << (length - 1)):
        if max_parts is not None and mask.bit_count() + 1 > max_parts:
            continue
        boundaries = [start]
        boundaries.extend(
            start + offset
            for offset in range(1, length)
            if mask & (1 << (offset - 1))
        )
        boundaries.append(stop)
        result.append(
            tuple(zip(boundaries[:-1], boundaries[1:], strict=True))
        )
    return result


def _is_compact(card: Card) -> bool:
    name = card.card_type.lower()
    return (
        any(hint in name for hint in _COMPACT_HINTS)
        or (card.char_count <= 80 and card.element_count <= 5)
    )


def _is_row_averse(card: Card) -> bool:
    name = card.card_type.lower()
    return any(hint in name for hint in _ROW_AVERSE_HINTS) or card.char_count > 320


def _leaf_span(node: LayoutNode) -> tuple[int, int]:
    if isinstance(node, CardNode):
        return node.card_index, node.card_index + 1
    spans = [_leaf_span(child) for child in node.children]
    return min(start for start, _ in spans), max(stop for _, stop in spans)


def _partition_signature(node: ContainerNode) -> tuple[object, ...]:
    """顶层切法签名（方向 + 每个子块的叶子区间），用于保留结构多样性。"""
    return (node.kind, tuple(_leaf_span(child) for child in node.children))


def _diverse_top(
    trees: list[ContainerNode],
    cards: list[Card],
    canvas: Canvas,
    limit: int,
) -> list[ContainerNode]:
    """按代理分排序，但每种顶层切法先至少保留一棵，避免 Beam 只剩同一切法的变体。"""
    ordered = sorted(
        trees,
        key=lambda tree: (_proxy_score(tree, cards, canvas), repr(canonical_key(tree))),
    )
    if len(ordered) <= limit:
        return ordered
    # 一半名额直接给代理分最好的树，另一半按切法签名轮转保多样性。
    selected: list[ContainerNode] = list(ordered[: limit // 2])
    selected_keys: set[tuple[object, ...]] = {
        canonical_key(tree) for tree in selected
    }
    cap = 1
    while len(selected) < limit:
        counts: dict[tuple[object, ...], int] = {}
        progressed = False
        for tree in ordered:
            if len(selected) >= limit:
                break
            key = canonical_key(tree)
            if key in selected_keys:
                continue
            signature = _partition_signature(tree)
            if counts.get(signature, 0) >= cap:
                continue
            counts[signature] = counts.get(signature, 0) + 1
            selected.append(tree)
            selected_keys.add(key)
            progressed = True
        if not progressed:
            break
        cap += 1
    return selected


def _proxy_score(node: LayoutNode, cards: list[Card], canvas: Canvas) -> float:
    """仅用于控制搜索宽度；最终排序由 scoring.py 完成。"""
    container_count = 0
    max_depth = 0
    row_penalty = 0.0

    def visit(current: LayoutNode, depth: int) -> None:
        nonlocal container_count, max_depth, row_penalty
        if isinstance(current, CardNode):
            return
        container_count += 1
        max_depth = max(max_depth, depth)
        if current.kind == "row":
            capacity = max(1, int((canvas.width + canvas.gap) / (180 + canvas.gap)))
            row_penalty += max(0, len(current.children) - capacity) * 2.0
            direct_cards = [
                cards[child.card_index]
                for child in current.children
                if isinstance(child, CardNode)
            ]
            row_penalty += sum(1.5 for card in direct_cards if _is_row_averse(card))
            compact_count = sum(_is_compact(card) for card in direct_cards)
            if 2 <= compact_count == len(direct_cards) <= 4:
                row_penalty -= 0.7
            # 同类成行（指标带、画廊）是人工布局的常见形态，给一点奖励。
            if len(direct_cards) >= 2 and len(
                {card.card_type for card in direct_cards}
            ) == 1:
                row_penalty -= 0.7
        for child in current.children:
            visit(child, depth + 1)

    visit(node, 1)
    root_penalty = (
        2.0
        if isinstance(node, ContainerNode)
        and node.kind == "row"
        and canvas.width < 600
        else 0.0
    )
    return row_penalty + root_penalty + container_count * 0.08 + max_depth * 0.04


def generate_candidates(
    cards: list[Card],
    canvas: Canvas,
    *,
    max_depth: int = 5,
    beam_width: int = 256,
) -> list[ContainerNode]:
    """生成规范化候选树。

    容器方向逐层交替，因此不会出现 row 套 row 之类的等价冗余结构。每个
    区间按代理分保留候选，但每种顶层切法至少留一棵，避免结构多样性被
    同一切法的变体挤掉。默认深度 5 是为了覆盖「标题+侧栏+主区再嵌套」的人工树。
    """
    if not cards:
        raise ValueError("至少需要一张 Card")
    if max_depth < 1 or beam_width < 2:
        raise ValueError("max_depth 至少为 1，beam_width 至少为 2")

    # 长页面避免枚举指数级的全部切分：每层最多拆成 4 组，并进一步收窄
    # 子候选组合。直接平铺仍由每个区间的 direct 候选覆盖。
    large_input = len(cards) > 9
    # 大卡数限深一层、收窄 Beam，否则候选量指数膨胀（深嵌套本身也被评分罚）。
    search_depth = min(max_depth, 4) if large_input else max_depth
    beam = min(beam_width, 64) if large_input else beam_width

    @lru_cache(maxsize=None)
    def build(
        start: int,
        stop: int,
        kind: LayoutKind,
        depth: int,
    ) -> tuple[ContainerNode, ...]:
        direct = ContainerNode(
            kind,
            tuple(CardNode(index) for index in range(start, stop)),
        )
        found = {canonical_key(direct): direct}
        if stop - start <= 1 or depth >= search_depth:
            return (direct,)

        other = _opposite(kind)
        child_limit = (
            max(4, min(16, beam // 16))
            if large_input
            else max(8, min(64, beam // 4))
        )
        combination_limit = (
            max(32, beam // 2) if large_input else beam * 2
        )
        for segments in _compositions(
            start,
            stop,
            max_parts=4 if large_input else None,
        ):
            choices: list[tuple[LayoutNode, ...]] = []
            for segment_start, segment_stop in segments:
                if segment_stop - segment_start == 1:
                    choices.append((CardNode(segment_start),))
                else:
                    # 子候选返回值是多样性顺序；父层组合时按代理分取前若干个。
                    subtrees = sorted(
                        build(segment_start, segment_stop, other, depth + 1),
                        key=lambda tree: (
                            _proxy_score(tree, cards, canvas),
                            repr(canonical_key(tree)),
                        ),
                    )
                    choices.append(tuple(subtrees[:child_limit]))

            for children in islice(product(*choices), combination_limit):
                candidate = ContainerNode(kind, tuple(children))
                found[canonical_key(candidate)] = candidate

            if len(found) > beam * 8:
                best = _diverse_top(list(found.values()), cards, canvas, beam * 3)
                found = {canonical_key(tree): tree for tree in best}

        return tuple(_diverse_top(list(found.values()), cards, canvas, beam))

    roots = [
        *build(0, len(cards), "column", 1),
        *build(0, len(cards), "row", 1),
    ]
    unique = {canonical_key(root): root for root in roots}
    result = list(unique.values())
    for root in result:
        validate_tree(root, len(cards))
    return result
