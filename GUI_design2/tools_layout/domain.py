"""布局搜索使用的纯数据结构。

所有节点都不可变，便于候选去重和缓存。CardNode 只保存输入序号，因此任何
生成结果都不会修改、遗漏或重排 Card 内容。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


LayoutKind = Literal["row", "column"]


@dataclass(frozen=True)
class Card:
    index: int
    card_type: str
    psuip: str
    char_count: int = 0
    token_count: int = 0
    element_count: int = 0


@dataclass(frozen=True)
class CardNode:
    card_index: int


@dataclass(frozen=True)
class ContainerNode:
    kind: LayoutKind
    children: tuple["LayoutNode", ...]


LayoutNode: TypeAlias = CardNode | ContainerNode


@dataclass(frozen=True)
class Canvas:
    width: float
    height: float
    gap: float = 16.0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("画布宽高必须大于 0")
        if self.gap < 0:
            raise ValueError("间距不能小于 0")


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Candidate:
    tree: ContainerNode
    score: float
    penalties: dict[str, float]


def node_to_dict(node: LayoutNode) -> dict[str, object]:
    if isinstance(node, CardNode):
        return {"kind": "card", "cardIndex": node.card_index}
    return {
        "kind": node.kind,
        "children": [node_to_dict(child) for child in node.children],
    }


def node_from_dict(data: dict[str, object]) -> LayoutNode:
    kind = data.get("kind")
    if kind == "card":
        return CardNode(int(data["cardIndex"]))  # type: ignore[arg-type]
    if kind not in ("row", "column"):
        raise ValueError(f"未知布局节点类型：{kind!r}")
    raw_children = data.get("children")
    if not isinstance(raw_children, list):
        raise ValueError("容器节点缺少 children")
    return ContainerNode(
        kind,
        tuple(node_from_dict(child) for child in raw_children if isinstance(child, dict)),
    )


def canonical_key(node: LayoutNode) -> tuple[object, ...]:
    if isinstance(node, CardNode):
        return ("card", node.card_index)
    return (node.kind, *(canonical_key(child) for child in node.children))


def leaf_indices(node: LayoutNode) -> list[int]:
    if isinstance(node, CardNode):
        return [node.card_index]
    result: list[int] = []
    for child in node.children:
        result.extend(leaf_indices(child))
    return result


def validate_tree(root: ContainerNode, card_count: int) -> None:
    """验证候选树的硬约束，失败时抛出 ValueError。"""
    indices = leaf_indices(root)
    if indices != list(range(card_count)):
        raise ValueError(f"Card 必须按顺序且恰好出现一次，实际为 {indices}")

    def visit(node: LayoutNode, is_root: bool = False) -> None:
        if isinstance(node, CardNode):
            return
        if not node.children:
            raise ValueError("布局中不能有空容器")
        if not is_root and len(node.children) < 2:
            raise ValueError("非根容器不能只有一个子节点")
        for child in node.children:
            if isinstance(child, ContainerNode) and child.kind == node.kind:
                raise ValueError("相同方向的容器不能直接嵌套")
            visit(child)

    visit(root, is_root=True)


def render_psuip(root: ContainerNode, cards: list[Card]) -> str:
    """将布局树与完全未经修改的 Card 原文组合为平台 PSUIP。

    容器写法与平台源稿 data/gird_with_cardtype/*.psuip.md 及前端
    flexTree.toLayout2Psuip 一致：row/column 带 alignItems="stretch"。
    """

    def render(node: LayoutNode, depth: int) -> list[str]:
        indent = "  " * depth
        if isinstance(node, CardNode):
            return [
                f"{indent}{line}" if line else ""
                for line in cards[node.card_index].psuip.splitlines()
            ]
        lines = [f'{indent}<layout:{node.kind} alignItems="stretch">']
        for child in node.children:
            lines.extend(render(child, depth + 1))
        lines.append(f"{indent}</layout:{node.kind}>")
        return lines

    return "\n".join(["<layout:root>", *render(root, 1), "</layout:root>"]) + "\n"
