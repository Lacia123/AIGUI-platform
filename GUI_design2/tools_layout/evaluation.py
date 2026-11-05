"""使用已有人工布局检查候选覆盖率和评分排名。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .candidates import generate_candidates
from .domain import (
    Canvas,
    Card,
    CardNode,
    ContainerNode,
    LayoutNode,
    canonical_key,
    leaf_indices,
    node_from_dict,
)
from .scoring import score_tree


def _tree_depth(node: LayoutNode) -> int:
    if isinstance(node, CardNode):
        return 0
    return 1 + max(_tree_depth(child) for child in node.children)


def _intervals_ok(node: LayoutNode) -> bool:
    if isinstance(node, CardNode):
        return True
    for child in node.children:
        leaves = leaf_indices(child)
        if leaves != list(range(min(leaves), max(leaves) + 1)):
            return False
        if not _intervals_ok(child):
            return False
    return True


def uncoverable_reason(target: ContainerNode, card_count: int, max_depth: int) -> str | None:
    """人工树在当前搜索空间里根本不存在时给出原因，与 Beam 剪枝失败区分。"""
    if leaf_indices(target) != list(range(card_count)):
        return "leaf_order"
    if not _intervals_ok(target):
        return "non_interval"
    if _tree_depth(target) > max_depth:
        return "depth"
    return None


def _dataset_cards(raw_cards: list[dict[str, Any]]) -> list[Card]:
    result: list[Card] = []
    for index, raw in enumerate(raw_cards):
        card_type = str(raw.get("type", "unknownCard"))
        label = str(raw.get("label", ""))
        psuip = f"<{card_type}><label>{label}</label></{card_type}>"
        result.append(
            Card(
                index=index,
                card_type=card_type,
                psuip=psuip,
                char_count=len(label),
                token_count=max(1, len(label)),
                element_count=1,
            )
        )
    return result


def evaluate_dataset(
    dataset_path: str | Path,
    *,
    beam_width: int = 256,
    max_depth: int = 5,
    limit: int | None = None,
) -> dict[str, object]:
    path = Path(dataset_path)
    if path.suffix == ".jsonl":
        episodes = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        episodes = payload["episodes"]
    if limit is not None:
        episodes = episodes[:limit]

    ranks: list[int] = []
    missing: list[str] = []
    uncoverable: list[str] = []
    human_scores: list[float] = []
    top1_scores: list[float] = []
    details: list[dict[str, object]] = []
    for episode in episodes:
        cards = _dataset_cards(episode["cards"])
        grid = episode["grid"]
        canvas = Canvas(
            float(grid["width"]),
            float(grid["height"]),
            float(grid.get("gap", 16)),
        )
        generated = generate_candidates(
            cards,
            canvas,
            max_depth=max_depth,
            beam_width=beam_width,
        )
        ranked = sorted(
            generated,
            key=lambda tree: (
                score_tree(tree, cards, canvas)[0],
                repr(canonical_key(tree)),
            ),
        )
        target = node_from_dict(episode["layout"])
        if not isinstance(target, ContainerNode):
            raise ValueError(f"{episode['id']}: 根节点必须是容器")
        target_key = canonical_key(target)
        rank = next(
            (
                index
                for index, tree in enumerate(ranked, start=1)
                if canonical_key(tree) == target_key
            ),
            None,
        )
        human_score = score_tree(target, cards, canvas)[0]
        top1_score = score_tree(ranked[0], cards, canvas)[0] if ranked else None
        human_scores.append(human_score)
        if top1_score is not None:
            top1_scores.append(top1_score)
        reason = uncoverable_reason(target, len(cards), max_depth)
        if rank is None:
            missing.append(str(episode["id"]))
            if reason is not None:
                uncoverable.append(str(episode["id"]))
        else:
            ranks.append(rank)
        details.append(
            {
                "id": episode["id"],
                "rank": rank,
                "candidateCount": len(ranked),
                "humanScore": round(human_score, 4),
                "top1Score": round(top1_score, 4) if top1_score is not None else None,
                "uncoverable": reason,
            }
        )

    total = len(episodes)
    gaps = [
        human - top1
        for human, top1 in zip(human_scores, top1_scores, strict=False)
    ]
    return {
        "episodes": total,
        "candidateCoverage": (total - len(missing)) / total if total else 0.0,
        "top1": sum(rank <= 1 for rank in ranks) / total if total else 0.0,
        "top3": sum(rank <= 3 for rank in ranks) / total if total else 0.0,
        "top5": sum(rank <= 5 for rank in ranks) / total if total else 0.0,
        "meanCoveredRank": sum(ranks) / len(ranks) if ranks else None,
        "meanHumanScore": sum(human_scores) / len(human_scores) if human_scores else None,
        "meanTop1Score": sum(top1_scores) / len(top1_scores) if top1_scores else None,
        "meanScoreGap": sum(gaps) / len(gaps) if gaps else None,
        "missingIds": missing,
        "uncoverableIds": uncoverable,
        "details": details,
    }
