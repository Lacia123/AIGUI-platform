"""布局几何：动作编解码、占用检测、掩码、观测拼装。

与 Gym 环境解耦，供 env.py 与 reward 中的 packability 调用。
"""

from __future__ import annotations

from typing import Any

import numpy as np


def encode_action(
    x: int,
    y: int,
    w: int,
    h: int,
    max_cols: int,
    max_card_w: int,
    max_card_h: int,
) -> int:
    """将 (x,y,w,h) 编码为单一离散动作 id。

    输入:
        x, y: 锚点格坐标（0-indexed）。
        w, h: 卡片宽高（1-indexed 格数，即占用 w×h 格）。
        max_cols, max_card_w, max_card_h: 编码空间上界。
    输出:
        整数 action id。
    逻辑:
        顺序 y → x → h → w 展开为四维笛卡尔积索引。
    """
    return (
        y * max_cols * max_card_w * max_card_h
        + x * max_card_w * max_card_h
        + (h - 1) * max_card_w
        + (w - 1)
    )


def decode_action(
    action: int,
    max_cols: int,
    max_card_w: int,
    max_card_h: int,
) -> tuple[int, int, int, int]:
    """decode_action 的逆操作。

    输入:
        action: 离散动作 id。
        max_cols, max_card_w, max_card_h: 与 encode_action 相同的上界。
    输出:
        (x, y, w, h)，w/h 为 1-indexed。
    """
    rem = int(action)
    w = rem % max_card_w + 1
    rem //= max_card_w
    h = rem % max_card_h + 1
    rem //= max_card_h
    x = rem % max_cols
    y = rem // max_cols
    return x, y, w, h


def can_place(occ: np.ndarray, x: int, y: int, w: int, h: int, cols: int, rows: int) -> bool:
    """判断矩形 [x,x+w) × [y,y+h) 是否在画布内且不与已占用格重叠。

    输入:
        occ: 占用矩阵，1=已占。
        x, y, w, h: 候选放置矩形。
        cols, rows: 当前 episode 实际画布尺寸。
    输出:
        True 表示可合法放置。
    """
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return False
    if x + w > cols or y + h > rows:
        return False
    region = occ[y : y + h, x : x + w]
    return bool(region.size) and not bool(region.any())


def place(occ: np.ndarray, x: int, y: int, w: int, h: int) -> None:
    """原地标记占用区 occ[y:y+h, x:x+w] = 1。"""
    occ[y : y + h, x : x + w] = 1


def sort_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按建议面积降序排序（可选工具，默认放卡顺序不调用）。

    输入/输出:
        卡片 dict 列表；键含 suggest_w/h 或 w/h。
    """
    return sorted(
        cards,
        key=lambda c: (
            -(c.get("suggest_w", c.get("w", 1)) * c.get("suggest_h", c.get("h", 1))),
            -c.get("suggest_w", c.get("w", 1)),
            -c.get("suggest_h", c.get("h", 1)),
            c["id"],
        ),
    )


def card_suggest_wh(card: dict[str, Any]) -> tuple[int, int]:
    """读取卡片建议尺寸，供 packability 等启发式使用。

    输入:
        card: 含 suggest_w/h；兼容旧字段 w/h。
    输出:
        (w, h) 整数元组。
    """
    return int(card.get("suggest_w", card["w"])), int(card.get("suggest_h", card["h"]))


def cards_from_episode(ep: dict[str, Any]) -> list[dict[str, Any]]:
    """从 dataset episode 构建待放置队列。

    输入:
        ep: jsonl 中的一条 episode，含 cards_wh、target_xy、可选 cards。
    输出:
        卡片列表，顺序与 cards_wh 一致。每项含:
            id, suggest_w/h, expert_w/h, expert_x/y。
    逻辑:
        cards_wh 提供建议尺寸；cards/target_xy 提供专家布局用于 imitation。
    """
    expert_xy = {t["id"]: t for t in ep.get("target_xy", [])}
    expert_full = {c["id"]: c for c in ep.get("cards", [])}
    cards = []
    for c in ep["cards_wh"]:
        cid = str(c["id"])
        ex_xy = expert_xy.get(cid)
        ex_full = expert_full.get(cid)
        suggest_w, suggest_h = int(c["w"]), int(c["h"])
        expert_w = int(ex_full["w"]) if ex_full else suggest_w
        expert_h = int(ex_full["h"]) if ex_full else suggest_h
        cards.append(
            {
                "id": cid,
                "suggest_w": suggest_w,
                "suggest_h": suggest_h,
                "expert_w": expert_w,
                "expert_h": expert_h,
                "expert_x": int(ex_xy["x"]) if ex_xy else None,
                "expert_y": int(ex_xy["y"]) if ex_xy else None,
            }
        )
    return cards


def action_masks(
    occ: np.ndarray,
    cols: int,
    rows: int,
    max_cols: int,
    max_rows: int,
    max_card_w: int,
    max_card_h: int,
) -> np.ndarray:
    """枚举当前状态下所有合法 (x,y,w,h) 动作，供 MaskablePPO 使用。

    输入:
        occ: 当前占用矩阵。
        cols, rows: 本局画布尺寸。
        max_*: 编码与 padding 上界（mask 长度 = action_space_size）。
    输出:
        长度 action_space_size 的 bool 数组，True=可选动作。
    逻辑:
        四重循环遍历 x,y,w,h；can_place 过滤越界与重叠。
    """
    size = max_cols * max_rows * max_card_w * max_card_h
    mask = np.zeros(size, dtype=bool)
    for y in range(rows):
        for x in range(cols):
            w_max = min(max_card_w, cols - x)
            h_max = min(max_card_h, rows - y)
            for h in range(1, h_max + 1):
                for w in range(1, w_max + 1):
                    if can_place(occ, x, y, w, h, cols, rows):
                        idx = encode_action(x, y, w, h, max_cols, max_card_w, max_card_h)
                        mask[idx] = True
    return mask


def density(occ: np.ndarray, cols: int, rows: int) -> float:
    """计算画布占用率，用于终局 success_reward。

    输出:
        已占用格数 / (cols * rows)，范围 [0, 1]。
    """
    area = int(occ[:rows, :cols].sum())
    return area / float(cols * rows)


def greedy_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool:
    """贪心探测：剩余卡按建议尺寸是否仍可能全部放下。

    输入:
        occ: 当前占用（会 copy，不修改原矩阵）。
        remaining: 尚未放置的卡片队列。
    输出:
        True=存在一种按建议尺寸的贪心放法；False=空间已被切碎。
    逻辑:
        大卡优先，每卡扫描 (x,y) 找第一个可放位置；用于 packability 惩罚。
    """
    if not remaining:
        return True
    board = occ.copy()
    cards = sorted(
        remaining,
        key=lambda c: (
            -(card_suggest_wh(c)[0] * card_suggest_wh(c)[1]),
            -card_suggest_wh(c)[0],
            -card_suggest_wh(c)[1],
        ),
    )
    for card in cards:
        w, h = card_suggest_wh(card)
        found = False
        for y in range(max(0, rows - h + 1)):
            for x in range(max(0, cols - w + 1)):
                if can_place(board, x, y, w, h, cols, rows):
                    place(board, x, y, w, h)
                    found = True
                    break
            if found:
                break
        if not found:
            return False
    return True


def build_obs(
    *,
    occ: np.ndarray,
    queue: list[dict[str, Any]],
    cursor: int,
    cols: int,
    rows: int,
    max_cols: int,
    max_rows: int,
    max_cards: int,
    total_cards: int,
) -> dict[str, np.ndarray]:
    """拼装 MaskablePPO 使用的 Dict 观测。

    输入:
        occ, queue, cursor: 环境内部状态。
        cols/rows: 本局画布；max_*: 固定张量 padding 尺寸。
    输出:
        dict，键与 LayoutEnv.observation_space 一致:
            occupancy: (max_rows, max_cols) 占用 0/1
            current_card: (4,) [suggest_w, suggest_h, expert_w, expert_h] 归一化
            remaining: (max_cards, 2) 后续卡建议尺寸
            grid: (2,) [cols/max_cols, rows/max_rows]
            progress: (2,) [已放比例, 剩余比例]
    """
    occupancy = np.zeros((max_rows, max_cols), dtype=np.float32)
    occupancy[:rows, :cols] = occ[:rows, :cols].astype(np.float32)

    current = np.zeros(4, dtype=np.float32)
    if cursor < len(queue):
        c = queue[cursor]
        current[0] = c["suggest_w"] / max_cols
        current[1] = c["suggest_h"] / max_rows
        current[2] = c["expert_w"] / max_cols
        current[3] = c["expert_h"] / max_rows

    remaining = np.zeros((max_cards, 2), dtype=np.float32)
    for i, c in enumerate(queue[cursor : cursor + max_cards]):
        remaining[i, 0] = c["suggest_w"] / max_cols
        remaining[i, 1] = c["suggest_h"] / max_rows

    return {
        "occupancy": occupancy,
        "current_card": current,
        "remaining": remaining,
        "grid": np.array([cols / max_cols, rows / max_rows], dtype=np.float32),
        "progress": np.array(
            [
                cursor / max(1, total_cards),
                (total_cards - cursor) / max(1, total_cards),
            ],
            dtype=np.float32,
        ),
    }


def to_sequence(placed: list[dict[str, Any]]) -> str:
    """将已放置列表转为 (w,h,x,y) 序列字符串。

    输入:
        placed: [{id, w, h, x, y}, ...]。
    输出:
        如 "(2,1,0,0)(3,2,2,0)" 的紧凑字符串。
    """
    from .tools.layout_format import stringify_layout_sequence

    return stringify_layout_sequence(
        [(p["w"], p["h"], p["x"], p["y"]) for p in placed]
    )
