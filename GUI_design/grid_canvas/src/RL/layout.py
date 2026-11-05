"""布局几何：动作编解码、占用检测、掩码、观测拼装。

与 Gym 环境解耦，供 env.py 与 reward.py 调用。
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any

import numpy as np


def encode_action(
    w: int,
    h: int,
    max_card_w: int,
) -> int:
    """将 (w,h) 编码为单一离散动作 id。

    输入:
        w, h: 卡片宽高（1-indexed 格数，即占用 w×h 格）。
        max_card_w: 宽度编码上界。
    输出:
        整数 action id。
    """
    return (h - 1) * max_card_w + (w - 1)


def decode_action(
    action: int,
    max_card_w: int,
) -> tuple[int, int]:
    """encode_action 的逆操作。

    输入:
        action: 离散动作 id。
        max_card_w: 与 encode_action 相同的宽度上界。
    输出:
        (w, h)，均为 1-indexed。
    """
    rem = int(action)
    w = rem % max_card_w + 1
    rem //= max_card_w
    h = rem + 1
    return w, h


def top_left_empty_anchor(
    occ: np.ndarray,
    cols: int,
    rows: int,
) -> tuple[int, int] | None:
    """返回空白区最左上空格：先取最小 y，再取该行最小的 x。"""
    for y in range(rows):
        for x in range(cols):
            if not occ[y, x]:
                return x, y
    return None


def anchored_box(
    anchor_x: int,
    anchor_y: int,
    w: int,
    h: int,
) -> tuple[int, int, int, int]:
    """左上锚点即矩形左上角；宽度向右、高度向下。"""
    return anchor_x, anchor_y, w, h


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


def cards_from_episode(ep: dict[str, Any]) -> list[dict[str, Any]]:
    """从 dataset episode 构建待放置队列。

    输入:
        ep: clean schema v3 episode，含 card_queue 与可选 expert_cards。
    输出:
        卡片列表，顺序与 card_queue 一致。每项含 id/type/label/psuip；
        若为训练 episode，附加 expert_w/h/x/y，仅供 reward，build_obs 不读取。
    逻辑:
        输入队列不含任何几何 hint；模型预测 (w,h)，环境确定 (x,y)。
    """
    from .psuip_content import attach_psuip

    expert_by_id = {str(c["id"]): c for c in ep.get("expert_cards", [])}
    cards = []
    for c in ep["card_queue"]:
        cid = str(c["id"])
        expert = expert_by_id.get(cid) or {}
        type_ = c.get("type")
        label = c.get("label")
        psuip = c.get("psuip")
        card = {"id": cid}
        for name in ("x", "y", "w", "h"):
            value = expert.get(name)
            card[f"expert_{name}"] = int(value) if value is not None else None
        if type_:
            card["type"] = str(type_)
        if label:
            card["label"] = str(label)
        if psuip:
            card["psuip"] = str(psuip)
        cards.append(card)
    attach_psuip(cards, source_file=ep.get("source_file"))
    return cards


def aspect_ratio_ok(
    width: int,
    height: int,
    cols: int,
    rows: int,
    max_ratio: float,
) -> bool:
    """长宽比不超过 max_ratio。通栏或通高视为合法带，不受限。"""
    if width <= 0 or height <= 0:
        return False
    if width == cols or height == rows:
        return True
    return max(width, height) <= max_ratio * min(width, height) + 1e-9


def action_masks(
    occ: np.ndarray,
    cols: int,
    rows: int,
    max_card_w: int,
    max_card_h: int,
) -> np.ndarray:
    """枚举左上空白锚点处所有合法 (w,h)，逐矩形检查不规则空白区。"""
    size = max_card_w * max_card_h
    mask = np.zeros(size, dtype=bool)
    anchor = top_left_empty_anchor(occ, cols, rows)
    if anchor is None:
        return mask

    anchor_x, anchor_y = anchor
    w_max = min(max_card_w, cols - anchor_x)
    h_max = min(max_card_h, rows - anchor_y)
    for h in range(1, h_max + 1):
        for w in range(1, w_max + 1):
            x, y, _, _ = anchored_box(anchor_x, anchor_y, w, h)
            if can_place(occ, x, y, w, h, cols, rows):
                mask[encode_action(w, h, max_card_w)] = True

    return mask


def density(occ: np.ndarray, cols: int, rows: int) -> float:
    """计算画布占用率。

    输出:
        已占用格数 / (cols * rows)，范围 [0, 1]。
    """
    area = int(occ[:rows, :cols].sum())
    return area / float(cols * rows)


def card_expert_wh(card: dict[str, Any]) -> tuple[int, int] | None:
    """训练奖励读取专家尺寸；缺标注返回 None。该函数不得被 State 调用。"""
    ew, eh = card.get("expert_w"), card.get("expert_h")
    if ew is not None and eh is not None:
        return max(1, int(ew)), max(1, int(eh))
    return None


def expert_positions_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool | None:
    """按队列顺序把剩余卡放到各自 expert (x,y,w,h)；缺标注则返回 None。

    True = 标注续放仍可行（专家轨迹不应被 packability 误罚）。
    False = 当前占用已挡住标注位置。
    None = 有卡缺少 expert 坐标，无法用本检查。
    """
    if not remaining:
        return True
    boxes: list[tuple[int, int, int, int]] = []
    for card in remaining:
        ex, ey = card.get("expert_x"), card.get("expert_y")
        ew, eh = card.get("expert_w"), card.get("expert_h")
        if ex is None or ey is None or ew is None or eh is None:
            return None
        boxes.append((int(ex), int(ey), max(1, int(ew)), max(1, int(eh))))
    board = occ.copy()
    for x, y, w, h in boxes:
        if not can_place(board, x, y, w, h, cols, rows):
            return False
        place(board, x, y, w, h)
    return True


def greedy_expert_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool | None:
    """训练期贪心探测：剩余卡按 expert 尺寸是否仍可能全部放下。

    大卡优先，每卡扫描第一个可放锚点。注意：这是充分条件近似，
    可能假阴性。任一卡缺少专家尺寸时返回 None，不制造假 1×1。
    """
    if not remaining:
        return True
    sized: list[tuple[dict[str, Any], int, int]] = []
    for card in remaining:
        wh = card_expert_wh(card)
        if wh is None:
            return None
        sized.append((card, wh[0], wh[1]))
    board = occ.copy()
    sized.sort(key=lambda item: (-(item[1] * item[2]), -item[1], -item[2]))
    for _card, w, h in sized:
        if w > cols or h > rows:
            return False
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


def exact_expert_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
    max_states: int = 20_000,
) -> bool | None:
    """用带缓存的回溯判断专家尺寸是否存在任意合法装法。

    相同尺寸用计数表示以消除排列重复；每一步优先选择当前合法位置最少的
    尺寸。搜索超过 ``max_states`` 时返回 None，调用方跳过奖励，而不是把
    “尚未证明可放”误判为不可放。
    """
    sizes: list[tuple[int, int]] = []
    for card in remaining:
        wh = card_expert_wh(card)
        if wh is None:
            return None
        w, h = wh
        if w > cols or h > rows:
            return False
        sizes.append((w, h))
    if not sizes:
        return True

    occupied = 0
    for y in range(rows):
        for x in range(cols):
            if occ[y, x]:
                occupied |= 1 << (y * cols + x)
    free_area = cols * rows - occupied.bit_count()
    if sum(w * h for w, h in sizes) > free_area:
        return False

    counts_by_size = Counter(sizes)
    unique_sizes = tuple(sorted(counts_by_size))
    initial_counts = tuple(counts_by_size[size] for size in unique_sizes)
    placements: list[tuple[int, ...]] = []
    for w, h in unique_sizes:
        masks = []
        for y in range(rows - h + 1):
            for x in range(cols - w + 1):
                mask = 0
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        mask |= 1 << (yy * cols + xx)
                masks.append(mask)
        placements.append(tuple(masks))

    visited = 0

    @lru_cache(maxsize=None)
    def search(board: int, counts: tuple[int, ...]) -> bool | None:
        nonlocal visited
        visited += 1
        if visited > max_states:
            return None
        if not any(counts):
            return True

        candidates: list[tuple[int, list[int]]] = []
        for i, count in enumerate(counts):
            if count:
                valid_masks = [mask for mask in placements[i] if not board & mask]
                if not valid_masks:
                    return False
                candidates.append((i, valid_masks))
        size_index, valid_masks = min(candidates, key=lambda item: len(item[1]))
        next_counts = list(counts)
        next_counts[size_index] -= 1
        next_counts_tuple = tuple(next_counts)

        unresolved = False
        for mask in valid_masks:
            result = search(board | mask, next_counts_tuple)
            if result is True:
                return True
            unresolved |= result is None
        return None if unresolved else False

    return search(occupied, initial_counts)


def remaining_expert_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool | None:
    """训练期剩余专家卡是否仍可装下（只供 reward，不进入 State）。

    依次尝试：
      1. 专家坐标仍可直接续放；
      2. 专家尺寸贪心能找到一个可行解；
      3. 带缓存的精确回溯。

    精确搜索超出预算返回 None，使奖励保持中性，不再因贪心失败而误罚。
    """
    if not remaining:
        return True
    expert_ok = expert_positions_packable(occ, remaining, cols, rows)
    if expert_ok is True:
        return True
    greedy_ok = greedy_expert_packable(occ, remaining, cols, rows)
    if greedy_ok is True:
        return True
    return exact_expert_packable(occ, remaining, cols, rows)


def anchored_sequence_packable(
    occ: np.ndarray,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool | None:
    """按环境的左上锚点规则，依队列顺序放置剩余专家尺寸。"""
    board = occ.copy()
    for card in remaining:
        wh = card_expert_wh(card)
        if wh is None:
            return None
        anchor = top_left_empty_anchor(board, cols, rows)
        if anchor is None:
            return False
        w, h = wh
        x, y, _, _ = anchored_box(anchor[0], anchor[1], w, h)
        if not can_place(board, x, y, w, h, cols, rows):
            return False
        place(board, x, y, w, h)
    return True


def free_span_maps(
    occ: np.ndarray,
    cols: int,
    rows: int,
    max_cols: int,
    max_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    """每格向右 / 向下连续空闲格数，按画布上界归一化到 [0,1]。

    分母用 max_cols / max_rows 而不是本局 cols / rows，这样空棋盘原点
    在 5 列页是 5/8、在 8 列页是 8/8，CNN 能直接区分可拉宽度。
    """
    right = np.zeros((max_rows, max_cols), dtype=np.float32)
    down = np.zeros((max_rows, max_cols), dtype=np.float32)
    if cols <= 0 or rows <= 0:
        return right, down
    board = occ[:rows, :cols]
    for y in range(rows):
        run = 0
        for x in range(cols - 1, -1, -1):
            if board[y, x] == 0:
                run += 1
            else:
                run = 0
            right[y, x] = run / float(max(1, max_cols))
    for x in range(cols):
        run = 0
        for y in range(rows - 1, -1, -1):
            if board[y, x] == 0:
                run += 1
            else:
                run = 0
            down[y, x] = run / float(max(1, max_rows))
    return right, down


def free_left_map(
    occ: np.ndarray,
    cols: int,
    rows: int,
    max_cols: int,
    max_rows: int,
) -> np.ndarray:
    """每格向左连续空闲格数，按 max_cols 归一化。"""
    left = np.zeros((max_rows, max_cols), dtype=np.float32)
    for y in range(rows):
        run = 0
        for x in range(cols):
            if occ[y, x] == 0:
                run += 1
            else:
                run = 0
            left[y, x] = run / float(max(1, max_cols))
    return left


def psuip_content_features(psuip: str) -> dict[str, float]:
    """从可部署 PSUIP 文本提取轻量内容特征（不含专家几何）。"""
    from .card_types import PSUIP_LEN_NORM

    text = str(psuip or "")
    lower = text.lower()
    length = len(text.strip())
    return {
        "psuip_len_n": min(1.0, length / float(max(1.0, PSUIP_LEN_NORM))),
        "has_table": 1.0 if ("<table" in lower or "[table:" in lower) else 0.0,
        "has_list": 1.0
        if (
            "<ul" in lower
            or "<ol" in lower
            or "<li" in lower
            or "\n- " in text
            or "\n* " in text
        )
        else 0.0,
        "has_image": 1.0
        if ("<img" in lower or "![" in text or "pairedimagetext" in lower)
        else 0.0,
    }


def build_layout_stats(
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
) -> np.ndarray:
    """全局布局状态：行列、空闲率、剩余数量、进度、剩余最小面积；不含专家几何。"""
    from .card_types import LAYOUT_STATS_DIM, type_min_area

    stats = np.zeros(LAYOUT_STATS_DIM, dtype=np.float32)
    page_area = max(1, cols * rows)
    free = float(page_area - int(occ[:rows, :cols].sum())) if cols > 0 and rows > 0 else 0.0
    remaining = queue[cursor:]
    n_total = max(1, int(total_cards))
    remain_min = 0
    for card in remaining:
        area = type_min_area(card.get("type"))
        if area is not None:
            remain_min += area
    stats[0] = cols / max(1, max_cols)
    stats[1] = rows / max(1, max_rows)
    stats[2] = free / float(page_area)
    stats[3] = len(remaining) / float(max(1, max_cards))
    stats[4] = min(1.0, float(cursor) / float(n_total))
    stats[5] = min(1.0, remain_min / float(page_area))
    return stats


def build_obs(
    *,
    occ: np.ndarray,
    queue: list[dict[str, Any]],
    placed: list[dict[str, Any]],
    cursor: int,
    cols: int,
    rows: int,
    max_cols: int,
    max_rows: int,
    max_cards: int,
    total_cards: int,
) -> dict[str, np.ndarray]:
    """拼装 MaskablePPO 使用的 Dict 观测。

    输出:
        spatial: (7, max_rows, max_cols)
            0 占用；1 已放类型；2 页内掩码；
            3 向右空闲跨度；4 向下空闲跨度；5 向左空闲跨度；
            6 当前左上空白锚点
        cards: (max_cards, 22)
            type/status/xywh/canvas/index/remain/
            same_type_ordinal/total/remain/
            psuip_len/has_table/has_list/has_image/valid/
            min_w/min_h/area_share
            已放: 实际 (x,y,w,h)；当前/未放几何为 0；expert 不写入
        grid: (6,) layout_stats — 行列、空闲、剩余数量、进度、剩余最小面积
        cursor: (1,) 归一化进度 cursor / total_cards ∈ [0, 1]
    """
    from .card_types import (
        CARD_IDX_COLS,
        CARD_IDX_CONSECUTIVE_SAME,
        CARD_IDX_H,
        CARD_IDX_HAS_IMAGE,
        CARD_IDX_HAS_LIST,
        CARD_IDX_HAS_TABLE,
        CARD_IDX_AREA_SHARE,
        CARD_IDX_INDEX,
        CARD_IDX_MIN_H,
        CARD_IDX_MIN_W,
        CARD_IDX_PSUIP_LEN,
        CARD_IDX_REMAIN,
        CARD_IDX_ROWS,
        CARD_IDX_SAME_ORDINAL,
        CARD_IDX_SAME_REMAIN,
        CARD_IDX_SAME_TOTAL,
        CARD_IDX_STATUS,
        CARD_IDX_TYPE,
        CARD_IDX_VALID,
        CARD_IDX_W,
        CARD_IDX_X,
        CARD_IDX_Y,
        CARD_OBS_DIM,
        N_CARD_TYPES,
        SPATIAL_CHANNELS,
        SPATIAL_ANCHOR,
        SPATIAL_FREE_DOWN,
        SPATIAL_FREE_LEFT,
        SPATIAL_FREE_RIGHT,
        SPATIAL_OCC,
        SPATIAL_PAGE,
        SPATIAL_TYPE,
        STATUS_CURRENT,
        STATUS_PLACED,
        STATUS_REMAINING,
        type_id,
        type_min_area,
        type_min_wh,
    )

    spatial = np.zeros((SPATIAL_CHANNELS, max_rows, max_cols), dtype=np.float32)
    spatial[SPATIAL_OCC, :rows, :cols] = occ[:rows, :cols].astype(np.float32)
    spatial[SPATIAL_PAGE, :rows, :cols] = 1.0
    for p in placed:
        x, y = int(p["x"]), int(p["y"])
        w, h = int(p["w"]), int(p["h"])
        tid = type_id(p.get("type")) / max(1, N_CARD_TYPES)
        y1, x1 = min(rows, y + h), min(cols, x + w)
        if y < y1 and x < x1:
            spatial[SPATIAL_TYPE, max(0, y) : y1, max(0, x) : x1] = tid

    right, down = free_span_maps(occ, cols, rows, max_cols, max_rows)
    spatial[SPATIAL_FREE_RIGHT] = right
    spatial[SPATIAL_FREE_DOWN] = down
    spatial[SPATIAL_FREE_LEFT] = free_left_map(
        occ, cols, rows, max_cols, max_rows
    )
    anchor = top_left_empty_anchor(occ, cols, rows)
    if anchor is not None:
        spatial[SPATIAL_ANCHOR, anchor[1], anchor[0]] = 1.0

    placed_by_id = {str(p["id"]): p for p in placed}
    cards = np.zeros((max_cards, CARD_OBS_DIM), dtype=np.float32)
    n = min(len(queue), max_cards)
    n_total = max(1, int(total_cards))
    cols_n = cols / float(max(1, max_cols))
    rows_n = rows / float(max(1, max_rows))

    type_names = [str(c.get("type") or "") for c in queue[:n]]
    type_totals: dict[str, int] = {}
    for name in type_names:
        type_totals[name] = type_totals.get(name, 0) + 1
    type_seen: dict[str, int] = {}
    seq_min = 0
    for name in type_names:
        area = type_min_area(name)
        if area is not None:
            seq_min += area

    # cursor 归一化到 [0,1]；放完后为 1.0
    cursor_obs = min(1.0, float(max(0, cursor)) / float(n_total))
    for i in range(n):
        c = queue[i]
        typ = type_names[i]
        type_seen[typ] = type_seen.get(typ, 0) + 1
        ordinal = type_seen[typ]
        total_same = max(1, type_totals.get(typ, 1))
        remain_same = total_same - ordinal + 1
        content = psuip_content_features(str(c.get("psuip") or ""))

        cards[i, CARD_IDX_TYPE] = float(type_id(c.get("type")))
        if i < cursor:
            cards[i, CARD_IDX_STATUS] = STATUS_PLACED
            p = placed_by_id.get(str(c["id"]))
            if p is not None:
                cards[i, CARD_IDX_X] = int(p["x"]) / max(1, max_cols)
                cards[i, CARD_IDX_Y] = int(p["y"]) / max(1, max_rows)
                cards[i, CARD_IDX_W] = int(p["w"]) / max(1, max_cols)
                cards[i, CARD_IDX_H] = int(p["h"]) / max(1, max_rows)
        else:
            cards[i, CARD_IDX_STATUS] = (
                STATUS_CURRENT if i == cursor else STATUS_REMAINING
            )
        cards[i, CARD_IDX_COLS] = cols_n
        cards[i, CARD_IDX_ROWS] = rows_n
        cards[i, CARD_IDX_INDEX] = i / float(n_total)
        cards[i, CARD_IDX_REMAIN] = (n_total - i) / float(n_total)
        cards[i, CARD_IDX_SAME_ORDINAL] = ordinal / float(total_same)
        cards[i, CARD_IDX_SAME_TOTAL] = total_same / float(max(1, max_cards))
        cards[i, CARD_IDX_SAME_REMAIN] = remain_same / float(total_same)
        run_len = 1
        while i + run_len < n and type_names[i + run_len] == typ:
            run_len += 1
        cards[i, CARD_IDX_CONSECUTIVE_SAME] = run_len / float(max(1, max_cards))
        cards[i, CARD_IDX_PSUIP_LEN] = float(content["psuip_len_n"])
        cards[i, CARD_IDX_HAS_TABLE] = float(content["has_table"])
        cards[i, CARD_IDX_HAS_LIST] = float(content["has_list"])
        cards[i, CARD_IDX_HAS_IMAGE] = float(content["has_image"])
        cards[i, CARD_IDX_VALID] = 1.0
        minimum = type_min_wh(typ)
        if minimum is not None:
            cards[i, CARD_IDX_MIN_W] = minimum[0] / float(max(1, max_cols))
            cards[i, CARD_IDX_MIN_H] = minimum[1] / float(max(1, max_rows))
            min_area = max(1, minimum[0] * minimum[1])
            cards[i, CARD_IDX_AREA_SHARE] = (
                min_area / float(seq_min) if seq_min > 0 else 0.0
            )

    return {
        "spatial": spatial,
        "cards": cards,
        "grid": build_layout_stats(
            occ=occ,
            queue=queue,
            cursor=cursor,
            cols=cols,
            rows=rows,
            max_cols=max_cols,
            max_rows=max_rows,
            max_cards=max_cards,
            total_cards=total_cards,
        ),
        "cursor": np.array([cursor_obs], dtype=np.float32),
    }


def to_sequence(
    placed: list[dict[str, Any]],
    *,
    cols: int | None = None,
    rows: int | None = None,
) -> str:
    """将已放置列表转为可渲染序列（可选 grid:CxR 头 + 带 type 的卡片）。

    输入:
        placed: [{id, w, h, x, y, type?}, ...]。
        cols/rows: 本局画布；提供时写入 `grid:CxR;` 供页面直接定尺寸渲染。
    输出:
        如 `grid:13x8;(2,1,0,0,"textCard")(3,2,2,0,"targetStatCard")`。
    """
    from .tools.layout_format import stringify_layout_sequence

    return stringify_layout_sequence(
        [(p["w"], p["h"], p["x"], p["y"], p.get("type")) for p in placed],
        cols=cols,
        rows=rows,
    )
