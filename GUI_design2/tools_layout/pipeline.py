"""候选生成、评分和输出的端到端管线。"""

from __future__ import annotations

import json
from pathlib import Path

from .candidates import generate_candidates
from .domain import (
    Candidate,
    Canvas,
    Card,
    canonical_key,
    node_to_dict,
    render_psuip,
)
from .geometry import tree_to_grid_sequence
from .scoring import ScoreWeights, score_tree


def rank_layouts(
    cards: list[Card],
    canvas: Canvas,
    *,
    top_k: int = 3,
    max_depth: int = 5,
    beam_width: int = 256,
    weights: ScoreWeights = ScoreWeights(),
) -> list[Candidate]:
    if top_k < 1:
        raise ValueError("top_k 必须大于 0")
    trees = generate_candidates(
        cards,
        canvas,
        max_depth=max_depth,
        beam_width=beam_width,
    )
    ranked: list[Candidate] = []
    for tree in trees:
        score, penalties = score_tree(tree, cards, canvas, weights)
        ranked.append(Candidate(tree, score, penalties))
    ranked.sort(key=lambda item: (item.score, repr(canonical_key(item.tree))))
    return ranked[:top_k]


def candidates_to_dict(
    candidates: list[Candidate],
    cards: list[Card],
    canvas: Canvas,
) -> dict[str, object]:
    return {
        "canvas": {
            "width": canvas.width,
            "height": canvas.height,
            "gap": canvas.gap,
        },
        "cardCount": len(cards),
        "candidates": [
            {
                "rank": rank,
                "score": round(candidate.score, 6),
                "penalties": {
                    name: round(value, 6)
                    for name, value in candidate.penalties.items()
                },
                "layout": node_to_dict(candidate.tree),
                "psuip": render_psuip(candidate.tree, cards),
                "gridSequence": tree_to_grid_sequence(candidate.tree, cards, canvas),
            }
            for rank, candidate in enumerate(candidates, start=1)
        ],
    }


def write_results(
    output_dir: str | Path,
    candidates: list[Candidate],
    cards: list[Card],
    canvas: Canvas,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    result = candidates_to_dict(candidates, cards, canvas)
    result_path = directory / "candidates.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for rank, candidate in enumerate(candidates, start=1):
        (directory / f"candidate-{rank}.psuip.md").write_text(
            render_psuip(candidate.tree, cards),
            encoding="utf-8",
        )
    return result_path
