"""将前端 sampleLayouts 导出为 RL 训练数据集（JSON / JSONL）。"""

from __future__ import annotations

import json
from pathlib import Path

from .design_mockups import DESIGN_MOCKUP_SAMPLES
from .layout_format import stringify_layout_sequence
from .psuip_typed_samples import PSUIP_TYPED_SAMPLES, _c

# 单位格 228×216 + gap 16；cols/rows 由页面分辨率正向推导：
#   cols = floor((pageW + gap) / (cellW + gap))
CELL_W0 = 228
CELL_H0 = 216
GAP = 16

# 常见设备/画板像素（内容区）；格子数随单格变大而变少
PAGE_PRESETS: dict[str, tuple[int, int, str]] = {
    "phone": (390, 844, "手机"),
    "tablet": (768, 1024, "平板"),
    "desktop": (1280, 800, "桌面"),
    "dashboard": (1880, 680, "仪表盘"),
    "square": (800, 800, "方阵"),
}


def _grid_from_page(page_w: int, page_h: int) -> tuple[int, int]:
    cols = max(1, (int(page_w) + GAP) // (CELL_W0 + GAP))
    rows = max(1, (int(page_h) + GAP) // (CELL_H0 + GAP))
    return cols, rows


def _preset(pid: str, label_prefix: str, width: int, height: int) -> dict:
    cols, rows = _grid_from_page(width, height)
    return {
        "id": pid,
        "label": f"{label_prefix} {width}×{height}（{cols}×{rows} @228×216/16）",
        "width": width,
        "height": height,
        "cols": cols,
        "rows": rows,
        "cell_w": CELL_W0,
        "cell_h": CELL_H0,
        "cell": CELL_W0,
        "gap": GAP,
    }


PRESETS = {
    pid: _preset(pid, prefix, w, h)
    for pid, (w, h, prefix) in PAGE_PRESETS.items()
}

# 与 src/sampleLayouts.ts 同步：每张卡均含 type（dict via _c）
# 格网：phone1×3 / tablet3×4 / desktop5×3 / dashboard7×3 / square3×3
CLASSIC_SAMPLES: list[dict] = [
    {
        "id": "phone-feed",
        "preset_id": "phone",
        "label": "信息流",
        "description": "顶 / 中 / 底三行通栏（1×3）",
        "cards": [
            _c(1, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "commonStyleServiceListDesc", "列表"),
            _c(1, 1, 0, 2, "textCard", "底栏"),
        ],
    },
    {
        "id": "phone-landing",
        "preset_id": "phone",
        "label": "落地页",
        "description": "顶栏 + Hero + CTA（1×3）",
        "cards": [
            _c(1, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "heroCard", "Hero"),
            _c(1, 1, 0, 2, "textCard", "CTA"),
        ],
    },
    {
        "id": "phone-profile",
        "preset_id": "phone",
        "label": "个人主页",
        "description": "头图 + 内容 + 底栏（1×3）",
        "cards": [
            _c(1, 1, 0, 0, "heroCard", "头图"),
            _c(1, 1, 0, 1, "summaryCard", "内容"),
            _c(1, 1, 0, 2, "textCard", "底栏"),
        ],
    },
    {
        "id": "tablet-blog",
        "preset_id": "tablet",
        "label": "双栏博客",
        "description": "顶栏 + 主/侧 + 底（3×4）",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "顶栏"),
            _c(2, 2, 0, 1, "__rawMarkdown__", "主栏"),
            _c(1, 2, 2, 1, "summaryCard", "侧栏"),
            _c(3, 1, 0, 3, "textCard", "底栏"),
        ],
    },
    {
        "id": "tablet-gallery",
        "preset_id": "tablet",
        "label": "卡片画廊",
        "description": "顶栏 + 2×3 栅格 + 底（3×4）",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "showcaseCard", "卡1"),
            _c(1, 1, 1, 1, "showcaseCard", "卡2"),
            _c(1, 1, 2, 1, "showcaseCard", "卡3"),
            _c(1, 1, 0, 2, "showcaseCard", "卡4"),
            _c(1, 1, 1, 2, "showcaseCard", "卡5"),
            _c(1, 1, 2, 2, "showcaseCard", "卡6"),
            _c(3, 1, 0, 3, "textCard", "底栏"),
        ],
    },
    {
        "id": "tablet-dashboard",
        "preset_id": "tablet",
        "label": "仪表盘",
        "description": "侧栏 + KPI + 主区（3×4）",
        "cards": [
            _c(1, 4, 0, 0, "textCard", "侧栏"),
            _c(2, 1, 1, 0, "textCard", "标题"),
            _c(1, 1, 1, 1, "targetStatCard", "KPI A"),
            _c(1, 1, 2, 1, "targetStatCard", "KPI B"),
            _c(2, 2, 1, 2, "showcaseCard", "主图"),
        ],
    },
    {
        "id": "desktop-dashboard",
        "preset_id": "desktop",
        "label": "仪表盘壳",
        "description": "侧栏 + KPI + 主图（5×3）",
        "cards": [
            _c(1, 3, 0, 0, "textCard", "侧栏"),
            _c(4, 1, 1, 0, "textCard", "顶栏"),
            _c(1, 1, 1, 1, "targetStatCard", "KPI A"),
            _c(1, 1, 2, 1, "targetStatCard", "KPI B"),
            _c(1, 1, 3, 1, "targetStatCard", "KPI C"),
            _c(1, 1, 4, 1, "targetStatCard", "KPI D"),
            _c(2, 1, 1, 2, "showcaseCard", "主图"),
            _c(2, 1, 3, 2, "__rawMarkdown__", "明细"),
        ],
    },
    {
        "id": "desktop-holy-grail",
        "preset_id": "desktop",
        "label": "圣杯布局",
        "description": "顶栏 + 侧/主 + 底（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "summaryCard", "侧栏"),
            _c(4, 1, 1, 1, "__rawMarkdown__", "主内容"),
            _c(5, 1, 0, 2, "textCard", "底栏"),
        ],
    },
    {
        "id": "desktop-three-col",
        "preset_id": "desktop",
        "label": "三栏后台",
        "description": "顶栏 + 左/中/右 + 底（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "textCard", "左导航"),
            _c(3, 1, 1, 1, "__rawMarkdown__", "主区"),
            _c(1, 1, 4, 1, "summaryCard", "右侧栏"),
            _c(5, 1, 0, 2, "textCard", "底栏"),
        ],
    },
    {
        "id": "desktop-magazine",
        "preset_id": "desktop",
        "label": "杂志分栏",
        "description": "顶栏 + 主卡 + 右侧堆叠（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "顶栏"),
            _c(3, 2, 0, 1, "heroCard", "大主卡"),
            _c(2, 1, 3, 1, "summaryCard", "侧卡上"),
            _c(2, 1, 3, 2, "summaryCard", "侧卡下"),
        ],
    },
    {
        "id": "square-holy-grail",
        "preset_id": "square",
        "label": "圣杯布局",
        "description": "顶 + 侧/主 + 底（3×3）",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "顶栏"),
            _c(1, 1, 0, 1, "summaryCard", "侧栏"),
            _c(2, 1, 1, 1, "__rawMarkdown__", "主区"),
            _c(3, 1, 0, 2, "textCard", "底栏"),
        ],
    },
    {
        "id": "square-dashboard",
        "preset_id": "square",
        "label": "仪表盘",
        "description": "侧栏 + KPI + 主区（3×3）",
        "cards": [
            _c(1, 3, 0, 0, "textCard", "侧栏"),
            _c(2, 1, 1, 0, "textCard", "标题"),
            _c(1, 1, 1, 1, "targetStatCard", "KPI A"),
            _c(1, 1, 2, 1, "targetStatCard", "KPI B"),
            _c(2, 1, 1, 2, "showcaseCard", "主图"),
        ],
    },
    {
        "id": "square-gallery",
        "preset_id": "square",
        "label": "卡片画廊",
        "description": "九宫格（3×3）",
        "cards": [
            _c(1, 1, 0, 0, "showcaseCard", "卡1"),
            _c(1, 1, 1, 0, "showcaseCard", "卡2"),
            _c(1, 1, 2, 0, "showcaseCard", "卡3"),
            _c(1, 1, 0, 1, "showcaseCard", "卡4"),
            _c(1, 1, 1, 1, "showcaseCard", "卡5"),
            _c(1, 1, 2, 1, "showcaseCard", "卡6"),
            _c(1, 1, 0, 2, "showcaseCard", "卡7"),
            _c(1, 1, 1, 2, "showcaseCard", "卡8"),
            _c(1, 1, 2, 2, "showcaseCard", "卡9"),
        ],
    },
    {
        "id": "square-landing",
        "preset_id": "square",
        "label": "落地页",
        "description": "顶栏 + Hero + 双栏（3×3）",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "顶栏"),
            _c(3, 1, 0, 1, "heroCard", "Hero"),
            _c(1, 1, 0, 2, "summaryCard", "左栏"),
            _c(2, 1, 1, 2, "summaryCard", "右栏"),
        ],
    },
]

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
    normalized = [_normalize_card(i, raw_card) for i, raw_card in enumerate(raw["cards"])]
    # 阅读序：先上后下、同行左到右；再重编号 id。
    normalized.sort(key=lambda c: (c["y"], c["x"]))
    card_queue = []
    expert_cards = []
    for i, card in enumerate(normalized):
        card = {**card, "id": f"c{i}"}
        queue_card = {"id": card["id"]}
        if "type" in card:
            queue_card["type"] = card["type"]
        if "label" in card:
            queue_card["label"] = card["label"]
        if "color" in card:
            queue_card["color"] = card["color"]
        card_queue.append(queue_card)
        expert_cards.append(
            {
                "id": card["id"],
                "w": card["w"],
                "h": card["h"],
                "x": card["x"],
                "y": card["y"],
            }
        )

    sequence = stringify_layout_sequence(
        [
            (box["w"], box["h"], box["x"], box["y"], queue.get("type"))
            for queue, box in zip(card_queue, expert_cards)
        ]
    )
    ep = {
        "schema_version": 3,
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
            "cell_w": preset.get("cell_w", CELL_W0),
            "cell_h": preset.get("cell_h", CELL_H0),
            "gap": preset.get("gap", GAP),
        },
        "card_queue": card_queue,
        "expert_cards": expert_cards,
        "sequence": sequence,
        "n_cards": len(card_queue),
        "area": sum(c["w"] * c["h"] for c in expert_cards),
    }
    if raw.get("source_file"):
        ep["source_file"] = raw["source_file"]
    return ep


def build_dataset() -> dict:
    episodes = [build_episode(raw) for raw in RAW_SAMPLES]
    return {
        "name": "sample_layouts",
        "version": "3.0",
        "task": "layout_restore",
        "cell_w": CELL_W0,
        "cell_h": CELL_H0,
        "cell": CELL_W0,
        "gap": GAP,
        "format": {
            "input": "card_queue: [{id,type,label?}, ...] + grid",
            "target": "expert_cards: [{id,w,h,x,y}, ...]",
            "grid": "cols/rows = floor((page+gap)/(cell+gap))；cell=228×216 gap=16",
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
    out_dir = out_dir or Path(__file__).resolve().parents[1] / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    full = build_dataset()
    json_path = out_dir / "sample_layouts.json"
    jsonl_path = out_dir / "sample_layouts.jsonl"
    _write_dataset(full, json_path, jsonl_path)

    design_eps = [build_episode(raw) for raw in DESIGN_MOCKUP_SAMPLES]
    design_ds = {
        "name": "design_mockups",
        "version": "3.0",
        "task": "layout_restore",
        "source": "education_app_mockups",
        "n_episodes": len(design_eps),
        "episodes": design_eps,
    }
    design_json = out_dir / "design_mockups.json"
    design_jsonl = out_dir / "design_mockups.jsonl"
    _write_dataset(design_ds, design_json, design_jsonl)

    psuip_eps = [build_episode(raw) for raw in PSUIP_TYPED_SAMPLES]
    psuip_ds = {
        "name": "psuip_typed_layouts",
        "version": "3.0",
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
    print("presets:")
    for pid, p in data["presets"].items():
        print(f"  {pid}: {p['width']}x{p['height']} -> {p['cols']}x{p['rows']}")
    design_n = sum(1 for ep in data["episodes"] if str(ep["id"]).startswith("design-"))
    psuip_n = sum(1 for ep in data["episodes"] if str(ep["id"]).startswith("psuip-"))
    print(f"design_mockups={design_n}  psuip_typed={psuip_n}")
    for ep in data["episodes"]:
        if not str(ep["id"]).startswith("psuip-"):
            continue
        g = ep["grid"]
        types = [c.get("type", "?") for c in ep["card_queue"]]
        print(
            f"  {ep['id']:32} {g['cols']}x{g['rows']}  "
            f"n={ep['n_cards']:2}  types={types}"
        )
