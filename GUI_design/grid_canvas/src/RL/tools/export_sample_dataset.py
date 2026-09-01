"""将前端 sampleLayouts 导出为 RL 训练数据集（JSON / JSONL）。"""

from __future__ import annotations

import json
from pathlib import Path

from .design_mockups import DESIGN_MOCKUP_SAMPLES
from .layout_format import stringify_layout_sequence
from .psuip_typed_samples import PSUIP_TYPED_SAMPLES

# 与页面默认 cellW0/H0=80、gap=16 一致：
#   phone 390×844 → 4×8；tablet 768×1024 → 8×10；
#   desktop 1280×800 → 13×8；dashboard 1880×680 → 19×7；square 800×800 → 8×8
PRESETS = {
    "phone": {
        "id": "phone",
        "label": "手机 390×844（4×8 @80/16）",
        "width": 390,
        "height": 844,
        "cols": 4,
        "rows": 8,
        "cell": 80,
        "gap": 16,
    },
    "tablet": {
        "id": "tablet",
        "label": "平板 768×1024（8×10 @80/16）",
        "width": 768,
        "height": 1024,
        "cols": 8,
        "rows": 10,
        "cell": 80,
        "gap": 16,
    },
    "desktop": {
        "id": "desktop",
        "label": "桌面 1280×800（13×8 @80/16）",
        "width": 1280,
        "height": 800,
        "cols": 13,
        "rows": 8,
        "cell": 80,
        "gap": 16,
    },
    "dashboard": {
        "id": "dashboard",
        "label": "仪表盘 1880×680（19×7 @80/16）",
        "width": 1880,
        "height": 680,
        "cols": 19,
        "rows": 7,
        "cell": 80,
        "gap": 16,
    },
    "square": {
        "id": "square",
        "label": "方阵 800×800（8×8 @80/16）",
        "width": 800,
        "height": 800,
        "cols": 8,
        "rows": 8,
        "cell": 80,
        "gap": 16,
    },
}

# 与 src/sampleLayouts.ts 经典骨架保持同步：每项 cards 为 (w,h,x,y)
CLASSIC_SAMPLES: list[dict] = [
    {
        "id": "phone-feed",
        "preset_id": "phone",
        "label": "信息流",
        "description": "顶栏 + 列表行 + 底栏（4×8）",
        "cards": [
            (4, 1, 0, 0),
            (4, 1, 0, 1),
            (4, 1, 0, 2),
            (4, 1, 0, 3),
            (4, 1, 0, 4),
            (4, 1, 0, 5),
            (4, 1, 0, 6),
            (4, 1, 0, 7),
        ],
    },
    {
        "id": "phone-landing",
        "preset_id": "phone",
        "label": "落地页",
        "description": "顶栏 + Hero + 2×2 功能卡 + CTA",
        "cards": [
            (4, 1, 0, 0),
            (4, 2, 0, 1),
            (2, 2, 0, 3),
            (2, 2, 2, 3),
            (2, 2, 0, 5),
            (2, 2, 2, 5),
            (4, 1, 0, 7),
        ],
    },
    {
        "id": "phone-profile",
        "preset_id": "phone",
        "label": "个人主页",
        "description": "头图 + KPI + 内容块",
        "cards": [
            (4, 1, 0, 0),
            (4, 2, 0, 1),
            (2, 1, 0, 3),
            (2, 1, 2, 3),
            (4, 2, 0, 4),
            (4, 2, 0, 6),
        ],
    },
    {
        "id": "tablet-blog",
        "preset_id": "tablet",
        "label": "双栏博客",
        "description": "顶栏 + 主栏/侧栏 + 底栏",
        "cards": [
            (8, 1, 0, 0),
            (5, 8, 0, 1),
            (3, 8, 5, 1),
            (8, 1, 0, 9),
        ],
    },
    {
        "id": "tablet-gallery",
        "preset_id": "tablet",
        "label": "卡片画廊",
        "description": "顶栏 + 2×4 栅格 + 底栏",
        "cards": [
            (8, 1, 0, 0),
            (2, 2, 0, 1),
            (2, 2, 2, 1),
            (2, 2, 4, 1),
            (2, 2, 6, 1),
            (2, 2, 0, 3),
            (2, 2, 2, 3),
            (2, 2, 4, 3),
            (2, 2, 6, 3),
            (2, 2, 0, 5),
            (2, 2, 2, 5),
            (2, 2, 4, 5),
            (2, 2, 6, 5),
            (2, 2, 0, 7),
            (2, 2, 2, 7),
            (2, 2, 4, 7),
            (2, 2, 6, 7),
            (8, 1, 0, 9),
        ],
    },
    {
        "id": "tablet-dashboard",
        "preset_id": "tablet",
        "label": "仪表盘",
        "description": "侧栏 + KPI + 图表/明细",
        "cards": [
            (2, 10, 0, 0),
            (6, 1, 2, 0),
            (2, 1, 2, 1),
            (2, 1, 4, 1),
            (2, 1, 6, 1),
            (4, 6, 2, 2),
            (2, 6, 6, 2),
            (6, 2, 2, 8),
        ],
    },
    {
        "id": "desktop-dashboard",
        "preset_id": "desktop",
        "label": "仪表盘壳",
        "description": "侧栏 + KPI + 主图/侧栏 + 底表",
        "cards": [
            (2, 8, 0, 0),
            (11, 1, 2, 0),
            (3, 1, 2, 1),
            (3, 1, 5, 1),
            (2, 1, 8, 1),
            (3, 1, 10, 1),
            (7, 5, 2, 2),
            (4, 5, 9, 2),
            (11, 1, 2, 7),
        ],
    },
    {
        "id": "desktop-holy-grail",
        "preset_id": "desktop",
        "label": "圣杯布局",
        "description": "顶栏 + 侧栏/主内容 + 底栏",
        "cards": [
            (13, 1, 0, 0),
            (3, 6, 0, 1),
            (10, 6, 3, 1),
            (13, 1, 0, 7),
        ],
    },
    {
        "id": "desktop-three-col",
        "preset_id": "desktop",
        "label": "三栏后台",
        "description": "顶栏 + 左导航/主区/右 aside + 底栏",
        "cards": [
            (13, 1, 0, 0),
            (2, 6, 0, 1),
            (8, 6, 2, 1),
            (3, 6, 10, 1),
            (13, 1, 0, 7),
        ],
    },
    {
        "id": "desktop-magazine",
        "preset_id": "desktop",
        "label": "杂志分栏",
        "description": "顶栏 + 大主卡 + 右侧堆叠 + 底栏",
        "cards": [
            (13, 1, 0, 0),
            (8, 6, 0, 1),
            (5, 3, 8, 1),
            (5, 3, 8, 4),
            (13, 1, 0, 7),
        ],
    },
    {
        "id": "square-holy-grail",
        "preset_id": "square",
        "label": "圣杯布局",
        "description": "顶栏 + 侧栏/主区 + 底栏",
        "cards": [
            (8, 1, 0, 0),
            (2, 6, 0, 1),
            (6, 6, 2, 1),
            (8, 1, 0, 7),
        ],
    },
    {
        "id": "square-dashboard",
        "preset_id": "square",
        "label": "仪表盘",
        "description": "侧栏 + KPI + 图表/明细",
        "cards": [
            (2, 8, 0, 0),
            (6, 1, 2, 0),
            (2, 1, 2, 1),
            (2, 1, 4, 1),
            (2, 1, 6, 1),
            (4, 5, 2, 2),
            (2, 5, 6, 2),
            (6, 1, 2, 7),
        ],
    },
    {
        "id": "square-gallery",
        "preset_id": "square",
        "label": "卡片画廊",
        "description": "顶栏 + 2×3 栅格 + 底栏",
        "cards": [
            (8, 1, 0, 0),
            (2, 2, 0, 1),
            (2, 2, 2, 1),
            (2, 2, 4, 1),
            (2, 2, 6, 1),
            (2, 2, 0, 3),
            (2, 2, 2, 3),
            (2, 2, 4, 3),
            (2, 2, 6, 3),
            (2, 2, 0, 5),
            (2, 2, 2, 5),
            (2, 2, 4, 5),
            (2, 2, 6, 5),
            (8, 1, 0, 7),
        ],
    },
    {
        "id": "square-landing",
        "preset_id": "square",
        "label": "落地页",
        "description": "顶栏 + Hero + 双栏 + 底栏",
        "cards": [
            (8, 1, 0, 0),
            (8, 2, 0, 1),
            (4, 4, 0, 3),
            (4, 4, 4, 3),
            (8, 1, 0, 7),
        ],
    },
]

# 经典骨架 + 设计稿抽象 + PSUIP 自适应转网格
RAW_SAMPLES = CLASSIC_SAMPLES + DESIGN_MOCKUP_SAMPLES + PSUIP_TYPED_SAMPLES


def _normalize_card(i: int, raw_card) -> dict:
    """支持 (w,h,x,y) 元组或含 type/label 的 dict。"""
    cid = f"c{i}"
    if isinstance(raw_card, dict):
        w, h, x, y = int(raw_card["w"]), int(raw_card["h"]), int(raw_card["x"]), int(raw_card["y"])
        card = {"id": cid, "w": w, "h": h, "x": x, "y": y}
        if "type" in raw_card:
            card["type"] = str(raw_card["type"])
        if "label" in raw_card:
            card["label"] = str(raw_card["label"])
        if "color" in raw_card:
            card["color"] = str(raw_card["color"])
        return card
    w, h, x, y = raw_card
    return {"id": cid, "w": int(w), "h": int(h), "x": int(x), "y": int(y)}


def build_episode(raw: dict) -> dict:
    preset = PRESETS[raw["preset_id"]]
    cards = []
    cards_wh = []
    target_xy = []
    for i, raw_card in enumerate(raw["cards"]):
        card = _normalize_card(i, raw_card)
        cards.append(card)
        wh = {"id": card["id"], "w": card["w"], "h": card["h"]}
        if "type" in card:
            wh["type"] = card["type"]
        if "label" in card:
            wh["label"] = card["label"]
        cards_wh.append(wh)
        target_xy.append({"id": card["id"], "x": card["x"], "y": card["y"]})

    sequence = stringify_layout_sequence(
        [(c["w"], c["h"], c["x"], c["y"]) for c in cards]
    )
    ep = {
        "id": raw["id"],
        "label": raw["label"],
        "description": raw["description"],
        "preset_id": raw["preset_id"],
        "grid": {
            "cols": preset["cols"],
            "rows": preset["rows"],
            "width": preset["width"],
            "height": preset["height"],
            "label": preset["label"],
        },
        "cards": cards,
        "cards_wh": cards_wh,
        "target_xy": target_xy,
        "sequence": sequence,
        "n_cards": len(cards),
        "area": sum(c["w"] * c["h"] for c in cards),
    }
    if raw.get("source_file"):
        ep["source_file"] = raw["source_file"]
    return ep


def build_dataset() -> dict:
    episodes = [build_episode(raw) for raw in RAW_SAMPLES]
    return {
        "name": "sample_layouts",
        "version": "1.2",
        "task": "layout_restore",
        "cell": 80,
        "gap": 16,
        "format": {
            "card": "(w,h,x,y) 或 {w,h,x,y,type,label}",
            "input": "cards_wh: [{id,w,h,type?}, ...] + grid",
            "target": "target_xy: [{id,x,y}, ...] 或 cards / sequence",
            "grid": "cols/rows 由 page @ cell=80 gap=16 推导",
        },
        "presets": PRESETS,
        "n_episodes": len(episodes),
        "episodes": episodes,
    }


def _write_dataset(dataset: dict, json_path: Path, jsonl_path: Path) -> None:
    json_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with jsonl_path.open("w", encoding="utf-8") as f:
        for ep in dataset["episodes"]:
            f.write(json.dumps(ep, ensure_ascii=False) + "\n")


def export_dataset(out_dir: Path | None = None) -> tuple[Path, Path, Path, Path]:
    # 默认写到 RL/data/（对齐 rl_train 的 data/）
    out_dir = out_dir or Path(__file__).resolve().parents[1] / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    full = build_dataset()
    json_path = out_dir / "sample_layouts.json"
    jsonl_path = out_dir / "sample_layouts.jsonl"
    _write_dataset(full, json_path, jsonl_path)

    # 单独导出设计稿子集，便于只拿设计数据训练
    design_eps = [build_episode(raw) for raw in DESIGN_MOCKUP_SAMPLES]
    design_ds = {
        "name": "design_mockups",
        "version": "1.0",
        "task": "layout_restore",
        "source": "education_app_mockups",
        "n_episodes": len(design_eps),
        "episodes": design_eps,
    }
    design_json = out_dir / "design_mockups.json"
    design_jsonl = out_dir / "design_mockups.jsonl"
    _write_dataset(design_ds, design_json, design_jsonl)

    # PSUIP 自适应 → 网格（带 type）
    psuip_eps = [build_episode(raw) for raw in PSUIP_TYPED_SAMPLES]
    psuip_ds = {
        "name": "psuip_typed_layouts",
        "version": "1.0",
        "task": "typed_layout",
        "source": "data/gird_with_cardtype/*.psuip.md",
        "n_episodes": len(psuip_eps),
        "episodes": psuip_eps,
    }
    psuip_json = out_dir / "psuip_typed_layouts.json"
    psuip_jsonl = out_dir / "psuip_typed_layouts.jsonl"
    _write_dataset(psuip_ds, psuip_json, psuip_jsonl)

    return json_path, jsonl_path, design_json, design_jsonl, psuip_json, psuip_jsonl


if __name__ == "__main__":
    paths = export_dataset()
    for p in paths:
        print(f"wrote {p}")
    data = json.loads(paths[0].read_text(encoding="utf-8"))
    print(f"episodes={data['n_episodes']} (classic+design+psuip)")
    design_n = sum(1 for ep in data["episodes"] if str(ep["id"]).startswith("design-"))
    psuip_n = sum(1 for ep in data["episodes"] if str(ep["id"]).startswith("psuip-"))
    print(f"design_mockups={design_n}  psuip_typed={psuip_n}")
    for ep in data["episodes"]:
        if not str(ep["id"]).startswith("psuip-"):
            continue
        g = ep["grid"]
        types = [c.get("type", "?") for c in ep["cards"]]
        print(
            f"  {ep['id']:32} {g['cols']}x{g['rows']}  "
            f"n={ep['n_cards']:2}  types={types}"
        )
