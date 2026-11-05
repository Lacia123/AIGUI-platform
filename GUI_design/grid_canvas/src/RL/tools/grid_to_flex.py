"""把 RL/data 里的网格 episode 转成 GUI_design2 的 row/column AST。

断头台分割：找不穿过任何卡的水平/垂直切割，递归成有序树。
flex 权重取子树包围盒格数，渲染比例与原网格一致。

用法：
    python -m RL.tools.grid_to_flex
    python -m RL.tools.grid_to_flex --source sample
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from RL.config import DATA_DIR


def _bbox(items: list[dict]) -> dict[str, int]:
    x = min(it["x"] for it in items)
    y = min(it["y"] for it in items)
    right = max(it["x"] + it["w"] for it in items)
    bottom = max(it["y"] + it["h"] for it in items)
    return {"x": x, "y": y, "w": right - x, "h": bottom - y}


def _start(it: dict, axis: str) -> int:
    return int(it["x" if axis == "x" else "y"])


def _size(it: dict, axis: str) -> int:
    return int(it["w" if axis == "x" else "h"])


def _split_bands(items: list[dict], axis: str) -> list[list[dict]] | None:
    if len(items) <= 1:
        return None
    edges = sorted({_start(it, axis) for it in items} | {_start(it, axis) + _size(it, axis) for it in items})
    cuts: list[int] = []
    for edge in edges[1:-1]:
        if not any(_start(it, axis) < edge < _start(it, axis) + _size(it, axis) for it in items):
            cuts.append(edge)
    if not cuts:
        return None
    bounds = [edges[0], *cuts, edges[-1]]
    bands: list[list[dict]] = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        band = [it for it in items if a <= _start(it, axis) and _start(it, axis) + _size(it, axis) <= b]
        if band:
            bands.append(band)
    return bands if len(bands) >= 2 else None


def _card_node(card: dict, index: int) -> dict:
    return {
        "kind": "card",
        "cardIndex": index,
        "card": card,
        "flex": 1,
        "bbox": {"x": card["x"], "y": card["y"], "w": card["w"], "h": card["h"]},
    }


def _fallback(items: list[dict], index_of: dict[int, int]) -> dict:
    ordered = sorted(items, key=lambda it: (it["y"], it["x"]))
    rows: list[list[dict]] = []
    for it in ordered:
        if rows and rows[-1][0]["y"] == it["y"] and rows[-1][0]["h"] == it["h"]:
            rows[-1].append(it)
        else:
            rows.append([it])
    box = _bbox(items)
    if len(rows) == 1:
        row = rows[0]
        if len(row) == 1:
            return _card_node(row[0], index_of[id(row[0])])
        return {
            "kind": "row",
            "flex": 1,
            "bbox": box,
            "children": [{**_card_node(c, index_of[id(c)]), "flex": c["w"]} for c in row],
        }
    return {
        "kind": "column",
        "flex": 1,
        "bbox": box,
        "children": [{**_fallback(row, index_of), "flex": _bbox(row)["h"]} for row in rows],
    }


def _build(items: list[dict], index_of: dict[int, int]) -> dict:
    if len(items) == 1:
        return _card_node(items[0], index_of[id(items[0])])

    h_bands = _split_bands(items, "y")
    v_bands = _split_bands(items, "x")
    bands = h_bands
    kind = "column"
    if h_bands and v_bands:
        if len(v_bands) > len(h_bands):
            bands = v_bands
            kind = "row"
    elif v_bands:
        bands = v_bands
        kind = "row"
    elif not h_bands:
        return _fallback(items, index_of)

    box = _bbox(items)
    children = []
    for band in bands or []:
        child = _build(band, index_of)
        child["flex"] = child["bbox"]["w"] if kind == "row" else child["bbox"]["h"]
        children.append(child)
    return {"kind": kind, "children": children, "flex": 1, "bbox": box}


def cards_to_flex_tree(cards: list[dict]) -> dict:
    if not cards:
        return {"kind": "column", "children": [], "flex": 1, "bbox": {"x": 0, "y": 0, "w": 0, "h": 0}}
    ordered = sorted(cards, key=lambda it: (it["y"], it["x"]))
    index_of = {id(c): i for i, c in enumerate(ordered)}
    inner = _build(ordered, index_of)
    if inner["kind"] == "card":
        return {"kind": "column", "children": [inner], "flex": 1, "bbox": inner["bbox"]}
    return inner


def to_layout2_ast(node: dict) -> dict:
    if node["kind"] == "card":
        return {"kind": "card", "cardIndex": node["cardIndex"]}
    return {"kind": node["kind"], "children": [to_layout2_ast(c) for c in node["children"]]}


def to_layout2_actions(node: dict) -> list[str]:
    actions: list[str] = []

    def walk(n: dict, is_root: bool) -> None:
        if n["kind"] == "card":
            actions.append("PLACE_CARD")
            return
        if not is_root:
            actions.append("OPEN_ROW" if n["kind"] == "row" else "OPEN_COLUMN")
        for child in n["children"]:
            walk(child, False)
        if not is_root:
            actions.append("CLOSE")

    walk(node, True)
    return actions


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _stringify(node: dict, level: int) -> str:
    pad = "  " * level
    if node["kind"] == "card":
        card = node["card"]
        typ = card.get("type") or "card"
        label = card.get("label") or typ
        return f"{pad}<{typ}>\n{pad}  <label>{_escape(str(label))}</label>\n{pad}</{typ}>"
    open_tag = f"{pad}<layout:{node['kind']} alignItems=\"stretch\">"
    close_tag = f"{pad}</layout:{node['kind']}>"
    body = "\n".join(_stringify(c, level + 1) for c in node["children"])
    return f"{open_tag}\n{body}\n{close_tag}"


def to_layout2_psuip(node: dict) -> str:
    return f"<layout:root>\n{_stringify(node, 1)}\n</layout:root>\n"


def episode_to_flex(ep: dict) -> dict[str, Any]:
    queue = {c["id"]: c for c in ep.get("card_queue") or []}
    cards: list[dict] = []
    for box in ep.get("expert_cards") or []:
        meta = queue.get(box.get("id"), {})
        cards.append(
            {
                "id": box.get("id"),
                "type": meta.get("type") or "card",
                "label": meta.get("label"),
                "color": meta.get("color"),
                "x": int(box["x"]),
                "y": int(box["y"]),
                "w": int(box["w"]),
                "h": int(box["h"]),
            }
        )
    tree = cards_to_flex_tree(cards)
    ordered = sorted(cards, key=lambda it: (it["y"], it["x"]))
    return {
        "id": ep.get("id"),
        "label": ep.get("label"),
        "description": ep.get("description"),
        "preset_id": ep.get("preset_id"),
        "grid": ep.get("grid"),
        "cards": [
            {
                "id": c.get("id") or f"c{i}",
                "type": c.get("type") or "card",
                "label": c.get("label"),
                "color": c.get("color"),
            }
            for i, c in enumerate(ordered)
        ],
        "actions": to_layout2_actions(tree),
        "layout": to_layout2_ast(tree),
        "psuip": to_layout2_psuip(tree),
    }


_SOURCE_JSON = {
    "sample": "sample_layouts.json",
    "design": "design_mockups.json",
    "psuip": "psuip_typed_layouts.json",
}

LAYOUT2_DIR = DATA_DIR.parents[4] / "GUI_design2" / "layout2data"


def _load_jsonl(path: Path) -> list[dict]:
    episodes: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            episodes.append(json.loads(line))
    return episodes


def _preset_from_grid(grid: dict) -> str:
    key = f"{int(grid.get('cols') or 0)}x{int(grid.get('rows') or 0)}"
    return {"8x5": "wide8x5", "3x6": "tall3x6", "4x6": "tall4x6"}.get(key, "custom")


def _normalize_hand(ep: dict) -> dict:
    grid = ep.get("grid") or {}
    raw_id = str(ep.get("id") or "hand")
    ep_id = raw_id if raw_id.startswith("hand-") else f"hand-{raw_id}"
    label = ep.get("label") or ""
    return {
        **ep,
        "id": ep_id,
        "preset_id": _preset_from_grid(grid),
        "label": label if "×" in label else f"{grid.get('cols')}×{grid.get('rows')} · {raw_id}",
    }


def _extra_handcrafted() -> list[dict]:
    paths = [
        DATA_DIR / "handcrafted_layouts.jsonl",
        DATA_DIR / "test_data" / "handcrafted_layouts (1).jsonl",
    ]
    out: list[dict] = []
    for path in paths:
        if path.is_file():
            out.extend(_normalize_hand(ep) for ep in _load_jsonl(path))
    return out


def _load_episodes(source: str) -> tuple[Path, list[dict]]:
    if source == "handcrafted":
        path = DATA_DIR / "handcrafted_layouts.jsonl"
        return path, _extra_handcrafted()
    path = DATA_DIR / _SOURCE_JSON.get(source, "sample_layouts.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    episodes = list(data.get("episodes") or [])
    if source == "sample":
        episodes.extend(_extra_handcrafted())
    return path, episodes


def _write_layout2data(payload: dict, converted: list[dict]) -> Path:
    dest_dir = LAYOUT2_DIR
    psuip_dir = dest_dir / "psuip"
    dest_dir.mkdir(parents=True, exist_ok=True)
    psuip_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "flex_layouts.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest_dir / "flex_layouts.jsonl").write_text(
        "\n".join(json.dumps(ep, ensure_ascii=False) for ep in converted) + "\n",
        encoding="utf-8",
    )
    for ep in converted:
        (psuip_dir / f"{ep['id']}.psuip.md").write_text(str(ep.get("psuip") or ""), encoding="utf-8")
    return dest


def convert(source: str = "sample", out: Path | None = None) -> Path:
    src_path, episodes = _load_episodes(source)
    seen: set[str] = set()
    converted: list[dict] = []
    for ep in episodes:
        item = episode_to_flex(ep)
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        converted.append(item)
    payload = {
        "schema_version": 1,
        "task": "flex_layout",
        "source": "sample_layouts.json + handcrafted + testdata",
        "format": {
            "input": "cards: [{id,type,label?}]",
            "target": "layout AST (row/column/card) + OPEN/PLACE/CLOSE actions",
        },
        "n_episodes": len(converted),
        "episodes": converted,
    }
    (DATA_DIR / "flex_layouts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    dest = out or _write_layout2data(payload, converted)
    if out:
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="网格 episode → layout2 row/column")
    parser.add_argument("--source", default="sample", choices=("sample", "design", "psuip", "handcrafted"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    dest = convert(args.source, args.out)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
