"""卡片类型词表与观测 State 契约。0 = 空/未知/padding。"""

from __future__ import annotations

import json
from pathlib import Path

# 观测契约版本：维度或语义变更时递增；checkpoint 元数据需匹配。
OBS_SCHEMA_VERSION = 6

TYPE_NAMES = (
    "targetStatCard",
    "mistakesCard",
    "showcaseCard",
    "summaryCard",
    "textCard",
    "commonStyleServiceListDesc",
    "pairedImageTextCard",
    "heroCard",
    "Topology",
    "__rawMarkdown__",
    "[table:commonStyle]",
    "contentSummaryCard",
)

NAME_TO_ID = {name: i + 1 for i, name in enumerate(TYPE_NAMES)}
N_CARD_TYPES = len(TYPE_NAMES)
TYPE_VOCAB = N_CARD_TYPES + 1

# ---------------------------------------------------------------------------
# cards 行（expert 永不进 State）
# type_id, status, x, y, w, h,
# cols_n, rows_n, index_n, remain_n,
# same_type_ordinal_n, same_type_total_n, remaining_same_type_n,
# psuip_len_n, has_table, has_list, has_image,
# valid, consecutive_same_type_n,
# min_w_n, min_h_n, area_share_n
# 未放/当前: x/y/w/h 全为 0；已放: 实际几何。
# min_* / area_share 来自类型默认格，不是专家框。
# ---------------------------------------------------------------------------
CARD_OBS_DIM = 22
CARD_IDX_TYPE = 0
CARD_IDX_STATUS = 1
CARD_IDX_X = 2
CARD_IDX_Y = 3
CARD_IDX_W = 4
CARD_IDX_H = 5
CARD_IDX_COLS = 6
CARD_IDX_ROWS = 7
CARD_IDX_INDEX = 8
CARD_IDX_REMAIN = 9
CARD_IDX_SAME_ORDINAL = 10
CARD_IDX_SAME_TOTAL = 11
CARD_IDX_SAME_REMAIN = 12
CARD_IDX_PSUIP_LEN = 13
CARD_IDX_HAS_TABLE = 14
CARD_IDX_HAS_LIST = 15
CARD_IDX_HAS_IMAGE = 16
CARD_IDX_VALID = 17
CARD_IDX_CONSECUTIVE_SAME = 18
CARD_IDX_MIN_W = 19
CARD_IDX_MIN_H = 20
CARD_IDX_AREA_SHARE = 21

STATUS_REMAINING = 0.0
STATUS_CURRENT = 1.0
STATUS_PLACED = 2.0

# PSUIP 长度归一化上界（字符数）；超过按 1.0 截断。
PSUIP_LEN_NORM = 2048.0

# ---------------------------------------------------------------------------
# spatial 通道 (C, max_rows, max_cols)
# 0 占用；1 已放类型；2 页内掩码；
# 3 向右连续空闲；4 向下连续空闲；5 向左连续空闲；
# 6 当前“最上行最左空格”锚点
# ---------------------------------------------------------------------------
SPATIAL_CHANNELS = 7
SPATIAL_OCC = 0
SPATIAL_TYPE = 1
SPATIAL_PAGE = 2
SPATIAL_FREE_RIGHT = 3
SPATIAL_FREE_DOWN = 4
SPATIAL_FREE_LEFT = 5
SPATIAL_ANCHOR = 6

# ---------------------------------------------------------------------------
# grid / layout_stats (观测键仍为 "grid"，兼容 SB3 Dict 接口)
# [cols_n, rows_n, free_ratio, remain_count_ratio, progress, remain_min_area_n]
# remain_min_area_n = 剩余卡最小面积之和 / 画布格数
# ---------------------------------------------------------------------------
LAYOUT_STATS_DIM = 6
STAT_COLS = 0
STAT_ROWS = 1
STAT_FREE_RATIO = 2
STAT_REMAIN_COUNT = 3
STAT_PROGRESS = 4
STAT_REMAIN_MIN_AREA = 5


def type_id(name: str | None) -> int:
    """类型名 → id；未知为 0。"""
    if not name:
        return 0
    return NAME_TO_ID.get(str(name), 0)


def _load_type_min_wh() -> dict[str, tuple[int, int]]:
    """读取 type_defaults.json。文件缺失时返回空表。"""
    path = Path(__file__).resolve().parent / "data" / "min_size_seqs" / "type_defaults.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    defaults = raw.get("defaults") or {}
    out: dict[str, tuple[int, int]] = {}
    for name, size in defaults.items():
        if not isinstance(size, dict):
            continue
        w, h = size.get("w"), size.get("h")
        if w is None or h is None:
            continue
        out[str(name)] = (max(1, int(w)), max(1, int(h)))
    return out


TYPE_MIN_WH = _load_type_min_wh()


def type_min_wh(name: str | None) -> tuple[int, int] | None:
    """类型默认最小格 (w, h)。未知类型返回 None。"""
    if not name:
        return None
    return TYPE_MIN_WH.get(str(name))


def type_min_area(name: str | None) -> int | None:
    """类型默认最小面积。未知类型返回 None。"""
    wh = type_min_wh(name)
    if wh is None:
        return None
    return max(1, int(wh[0]) * int(wh[1]))
