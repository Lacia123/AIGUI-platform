"""随机画布 + 类型队列。只保留「按环境左上锚点能放完」的页。

可行性用类型最小格和份额带宽试放，不把试放坐标写成 expert。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__:
    from .. import config as cfg
    from ..card_types import TYPE_MIN_WH, type_min_area, type_min_wh
    from ..layout import anchored_box, can_place, place, top_left_empty_anchor
else:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL import config as cfg
    from RL.card_types import TYPE_MIN_WH, type_min_area, type_min_wh
    from RL.layout import anchored_box, can_place, place, top_left_empty_anchor

CANVASES = (
    (8, 5),
    (8, 4),
    (7, 3),
    (6, 4),
    (5, 3),
    (4, 6),
    (4, 4),
    (3, 6),
)
FILL_TYPES = (
    "textCard",
    "showcaseCard",
    "targetStatCard",
    "mistakesCard",
    "contentSummaryCard",
    "summaryCard",
    "heroCard",
    "Topology",
    "__rawMarkdown__",
    "pairedImageTextCard",
)
LABELS = {
    "textCard": "textCard",
    "showcaseCard": "showcase",
    "targetStatCard": "targetStat",
    "mistakesCard": "mistakes",
    "contentSummaryCard": "contentSummary",
    "summaryCard": "summary",
    "heroCard": "hero",
    "Topology": "Topology",
    "__rawMarkdown__": "rawMarkdown",
    "pairedImageTextCard": "pairedImage",
}
COLORS = {
    "textCard": "#5eb887",
    "showcaseCard": "#3d8bfd",
    "targetStatCard": "#e6a23c",
    "mistakesCard": "#d9776f",
    "contentSummaryCard": "#c4785a",
    "summaryCard": "#9b6bdf",
    "heroCard": "#3d8bfd",
    "Topology": "#5c6bc0",
    "__rawMarkdown__": "#7a8b9a",
    "pairedImageTextCard": "#2aa8a0",
}


def _shape_ok(w: int, h: int, min_w: int, min_h: int) -> bool:
    if min_w == min_h:
        return True
    if min_w > min_h:
        return w > h
    return h > w


def _size_candidates(
    typ: str,
    share: float,
    cols: int,
    rows: int,
    first_text: bool,
) -> list[tuple[int, int]]:
    minimum = type_min_wh(typ)
    if minimum is None:
        return [(1, 1)]
    min_w, min_h = minimum
    min_area = max(1, min_w * min_h)
    lo = max(1, int(share) - 1)
    hi = max(min_area, int(2 * share))
    out: list[tuple[int, int]] = []
    if first_text and typ == "textCard":
        for h in (1, 2):
            if cols * h <= hi * 1.05 or cols * h <= hi + 1:
                out.append((cols, h))
    for area in range(hi, lo - 1, -1):
        for h in range(1, rows + 1):
            if area % h:
                continue
            w = area // h
            if w < 1 or w > cols:
                continue
            if w * h + 1 < min_area:
                continue
            if not _shape_ok(w, h, min_w, min_h):
                continue
            out.append((w, h))
    if (min_w, min_h) not in out and min_w <= cols and min_h <= rows:
        out.append((min_w, min_h))
    seen: set[tuple[int, int]] = set()
    uniq: list[tuple[int, int]] = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def try_anchored_pack(
    types: list[str],
    cols: int,
    rows: int,
) -> list[dict[str, int]] | None:
    """按环境锚点试放。成功则返回见证框，失败返回 None。"""
    areas = [type_min_area(t) or 1 for t in types]
    seq = max(1, sum(areas))
    page = float(cols * rows)
    occ = np.zeros((rows, cols), dtype=np.int8)
    placed: list[dict[str, int]] = []
    for i, typ in enumerate(types):
        share = (areas[i] / float(seq)) * page
        anchor = top_left_empty_anchor(occ, cols, rows)
        if anchor is None:
            return None
        fitted = False
        for w, h in _size_candidates(typ, share, cols, rows, first_text=(i == 0)):
            x, y, _, _ = anchored_box(anchor[0], anchor[1], w, h)
            if can_place(occ, x, y, w, h, cols, rows):
                place(occ, x, y, w, h)
                placed.append({"w": w, "h": h, "x": x, "y": y})
                fitted = True
                break
        if not fitted:
            return None
    return placed


def sample_types(rng: random.Random, n: int) -> list[str]:
    types: list[str] = []
    if rng.random() < 0.75:
        types.append("textCard")
    if rng.random() < 0.55 and len(types) < n:
        types.extend(["targetStatCard"] * rng.randint(2, 4))
    if rng.random() < 0.4 and len(types) < n:
        types.append("showcaseCard")
    if rng.random() < 0.45 and len(types) < n:
        types.extend(["mistakesCard"] * rng.randint(2, 3))
    pool = [t for t in FILL_TYPES if t in TYPE_MIN_WH]
    while len(types) < n:
        types.append(rng.choice(pool))
    return types[:n]


def sample_episode(rng: random.Random, index: int) -> dict[str, Any] | None:
    cols, rows = rng.choice(CANVASES)
    page = cols * rows
    n = rng.randint(3, min(9, page // 2 + 2))
    types = sample_types(rng, n)
    mins = [type_min_area(t) or 1 for t in types]
    if sum(mins) > int(0.85 * page):
        return None
    if any((type_min_wh(t) or (99, 99))[0] > cols or (type_min_wh(t) or (99, 99))[1] > rows for t in types):
        return None
    witness = try_anchored_pack(types, cols, rows)
    if witness is None:
        return None
    queue = [
        {
            "id": f"c{i}",
            "type": typ,
            "label": LABELS.get(typ, typ),
            "color": COLORS.get(typ, "#3d8bfd"),
        }
        for i, typ in enumerate(types)
    ]
    return {
        "id": f"synth-{index:04d}",
        "label": "随机画布",
        "description": f"{cols}×{rows} 锚点可放完",
        "preset_id": "synth",
        "grid": {"cols": cols, "rows": rows},
        "n_cards": len(types),
        "area": page,
        "source_file": "synth",
        "schema_version": 3,
        "card_queue": queue,
        "expert_cards": [],
    }


def generate_episodes(n: int, seed: int = 0) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    attempts = 0
    while len(out) < n and attempts < n * 40:
        attempts += 1
        ep = sample_episode(rng, len(out) + 1)
        if ep is None:
            continue
        out.append(ep)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="生成随机画布、锚点可放完的 episode")
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--out",
        type=Path,
        default=cfg.DATA_DIR / "synth_layouts.jsonl",
    )
    args = parser.parse_args()
    episodes = generate_episodes(args.n, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for ep in episodes:
            handle.write(json.dumps(ep, ensure_ascii=False) + "\n")
    grids: dict[str, int] = {}
    for ep in episodes:
        key = f"{ep['grid']['cols']}x{ep['grid']['rows']}"
        grids[key] = grids.get(key, 0) + 1
    print(f"wrote {len(episodes)} episodes -> {args.out}")
    print("grids", dict(sorted(grids.items())))


if __name__ == "__main__":
    main()
