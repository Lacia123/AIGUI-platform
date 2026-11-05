"""为 8×5 手工标注页补每张卡的最小展示尺寸。

读取 handcrafted_layouts.jsonl 中的 8×5 页，按 card type 取
card_type_samples.json 样例，调用 check_min_size，把带 min_w/min_h 的
序列写到 data/min_size_seqs/。

用法:
  cd GUI_design/grid_canvas/src
  python -m RL.tools.gen_train_seq
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .. import config as cfg
    from ..data import iter_jsonl
    from ..layout_check import check_min_size, reset_client
else:
    src_dir = Path(__file__).resolve().parents[2]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL import config as cfg
    from RL.data import iter_jsonl
    from RL.layout_check import check_min_size, reset_client

GRID_COLS = 8
GRID_ROWS = 5
OUT_DIR_NAME = "min_size_seqs"


def min_size_dir() -> Path:
    """输出目录：RL/data/min_size_seqs/。"""
    return cfg.DATA_DIR / OUT_DIR_NAME


def load_card_type_samples() -> dict[str, str]:
    """读取 type → 裸 PSUIP 样例文本。"""
    path = cfg.DATA_DIR / "card_type_samples.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples = raw.get("samples") or {}
    return {
        str(k): str(v.get("psuip") or "").strip()
        for k, v in samples.items()
        if isinstance(v, dict) and str(v.get("psuip") or "").strip()
    }


def load_handcrafted_8x5(path: Path | None = None) -> list[dict[str, Any]]:
    """读取手工标注 jsonl，只保留 8×5 页面。"""
    src = path or cfg.handcrafted_jsonl()
    episodes = []
    for ep in iter_jsonl(src):
        grid = ep.get("grid") or {}
        if int(grid.get("cols") or 0) == GRID_COLS and int(grid.get("rows") or 0) == GRID_ROWS:
            episodes.append(ep)
    return episodes


def sample_body_for_type(type_name: str, samples: dict[str, str]) -> str:
    """按类型取样例；缺失时返回空串。"""
    return (samples.get(str(type_name or "")) or "").strip()


def min_size_sequence(ep: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    """专家几何 + 最小尺寸：`(w,h,x,y,type,minWxminH)`。"""
    expert_by_id = {str(c["id"]): c for c in ep.get("expert_cards") or []}
    parts: list[str] = []
    for card in cards:
        box = expert_by_id.get(str(card["id"])) or {}
        typ = str(card.get("type") or "")
        mw, mh = card.get("min_w"), card.get("min_h")
        min_tok = f"{mw}x{mh}" if mw is not None and mh is not None else "none"
        parts.append(
            f"({int(box.get('w', 0))},{int(box.get('h', 0))},"
            f"{int(box.get('x', 0))},{int(box.get('y', 0))},"
            f"{typ},{min_tok})"
        )
    return "".join(parts)


def annotate_card_min_size(
    card: dict[str, Any],
    *,
    samples: dict[str, str],
    columns: int,
    rows: int,
) -> dict[str, Any]:
    """给一张卡填样例、调 check_min_size，返回带最小尺寸的副本。"""
    out = dict(card)
    type_name = str(card.get("type") or "")
    psuip = sample_body_for_type(type_name, samples)
    out["psuip"] = psuip
    if not psuip:
        out["min_w"] = None
        out["min_h"] = None
        out["min_size"] = {
            "reachable": False,
            "valid": False,
            "messages": [f"missing card sample for type={type_name!r}"],
        }
        return out

    result = check_min_size(psuip, columns, rows, test=False)
    if not result.get("reachable"):
        reset_client()
        result = check_min_size(psuip, columns, rows, test=False)
    out["min_w"] = result.get("min_w")
    out["min_h"] = result.get("min_h")
    out["min_size"] = {
        "reachable": result.get("reachable"),
        "valid": result.get("valid"),
        "start_w": result.get("start_w"),
        "start_h": result.get("start_h"),
        "tendency": result.get("tendency") or [],
        "card_name": result.get("card_name") or "",
        "messages": result.get("messages") or [],
    }
    return out


def annotate_episode(
    ep: dict[str, Any],
    *,
    samples: dict[str, str],
) -> dict[str, Any]:
    """给一页的每张卡补最小尺寸，写出新序列。"""
    grid = ep.get("grid") or {}
    cols = int(grid.get("cols") or GRID_COLS)
    rows = int(grid.get("rows") or GRID_ROWS)
    cards = []
    for i, card in enumerate(ep.get("card_queue") or []):
        type_name = str(card.get("type") or "")
        print(
            f"  {ep.get('id')} [{i + 1}/{len(ep.get('card_queue') or [])}] "
            f"{type_name} -> check_min_size({cols}x{rows})",
            flush=True,
        )
        cards.append(
            annotate_card_min_size(card, samples=samples, columns=cols, rows=rows)
        )
    out = dict(ep)
    out["card_queue"] = cards
    out["min_size_sequence"] = min_size_sequence(ep, cards)
    out["min_size_grid"] = {"cols": cols, "rows": rows}
    return out


def save_min_size_episodes(
    episodes: list[dict[str, Any]],
    out_dir: Path | None = None,
) -> Path:
    """每页一个 json，另外写一份汇总 jsonl。返回目录。"""
    dest = out_dir or min_size_dir()
    dest.mkdir(parents=True, exist_ok=True)
    jsonl_path = dest / "handcrafted_8x5.min_size.jsonl"
    index: list[dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for ep in episodes:
            ep_id = str(ep.get("id") or "episode")
            page_path = dest / f"{ep_id}.json"
            page_path.write_text(
                json.dumps(ep, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            handle.write(json.dumps(ep, ensure_ascii=False) + "\n")
            cards = ep.get("card_queue") or []
            index.append(
                {
                    "id": ep_id,
                    "n_cards": len(cards),
                    "file": page_path.name,
                    "min_size_sequence": ep.get("min_size_sequence"),
                    "ok": all(
                        (c.get("min_w") is not None and c.get("min_h") is not None)
                        for c in cards
                    ),
                }
            )
    (dest / "index.json").write_text(
        json.dumps(
            {
                "grid": f"{GRID_COLS}x{GRID_ROWS}",
                "n_episodes": len(episodes),
                "jsonl": jsonl_path.name,
                "episodes": index,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dest


def generate_min_size_seqs(
    *,
    source: Path | None = None,
    out_dir: Path | None = None,
) -> Path:
    """读取 8×5 手工页 → 样例 POST → check_min_size → 写 data/min_size_seqs。"""
    cfg.LAYOUT_CHECK_TIMEOUT = max(float(cfg.LAYOUT_CHECK_TIMEOUT), 60.0)
    reset_client()
    samples = load_card_type_samples()
    episodes = load_handcrafted_8x5(source)
    if not episodes:
        raise ValueError("没有 8×5 手工标注页面")
    annotated = [annotate_episode(ep, samples=samples) for ep in episodes]
    return save_min_size_episodes(annotated, out_dir)


def main() -> None:
    dest = generate_min_size_seqs()
    index = json.loads((dest / "index.json").read_text(encoding="utf-8"))
    print(f"wrote {dest}")
    print(f"episodes={index['n_episodes']} grid={index['grid']}")
    for item in index["episodes"]:
        flag = "ok" if item["ok"] else "missing"
        print(f"  [{flag}] {item['id']} n={item['n_cards']} {item['min_size_sequence']}")


if __name__ == "__main__":
    main()
