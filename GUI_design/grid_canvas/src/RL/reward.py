"""奖励函数：合法性、样式、终局与 packability。

每步总奖励在 env.step 中组装:
    reward = legality + style + packability + terminal(仅结束时)
权重常量见 config.py。
"""

from __future__ import annotations

from typing import Any


def legality_reward(valid: bool, valid_reward: float, invalid_penalty: float) -> float:
    """单步合法性奖励。

    输入:
        valid: 动作是否通过 can_place。
        valid_reward / invalid_penalty: config 中的 ± 系数。
    输出:
        合法 → valid_reward；非法 → invalid_penalty。
    """
    return valid_reward if valid else invalid_penalty


def _overlap(a0: int, a1: int, b0: int, b1: int) -> int:
    """一维闭区间 [a0,a1) 与 [b0,b1) 的重合长度（格数）。"""
    return max(0, min(a1, b1) - max(a0, b0))


def _size_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    """两卡宽高相对差异 → 相似度 [0,1]。

    输入:
        a, b: 含 w/h 的卡片 dict（通常为已放置卡）。
    输出:
        1=完全相同，差异越大越趋近 0。
    """
    dw = abs(a["w"] - b["w"]) / max(a["w"], b["w"])
    dh = abs(a["h"] - b["h"]) / max(a["h"], b["h"])
    return max(0.0, 1.0 - (dw + dh) / 2.0)


def _reading_order_score(
    card: dict[str, Any],
    x: int,
    y: int,
    placed: list[dict[str, Any]],
    *,
    cols: int,
    rows: int,
    cursor: int,
    total_cards: int,
) -> float:
    """阅读顺序分 [0,1]：先放偏左上，后放偏右下。

    输入:
        card, x, y: 当前卡及锚点。
        placed: 已放置列表。
        cursor / total_cards: 放置进度。
    逻辑:
        1) 绝对：按 cursor 在「期望左上/右下」间插值，比较卡中心位置。
        2) 相对：新卡 (y,x) 应不早于多数旧卡。
        两者各 50% 加权。
    """
    cx = (x + 0.5 * card["w"]) / max(1, cols)
    cy = (y + 0.5 * card["h"]) / max(1, rows)
    top_leftness = 1.0 - 0.5 * (cx + cy)

    progress = cursor / max(1, total_cards - 1)
    schedule = (1.0 - progress) * top_leftness + progress * (1.0 - top_leftness)

    if not placed:
        return schedule

    older_before = sum(
        1 for p in placed if (int(p["y"]), int(p["x"])) <= (y, x)
    )
    relative = older_before / len(placed)
    return 0.5 * schedule + 0.5 * relative


def _origin_anchor_score(x: int, y: int, cursor: int) -> float:
    """首卡原点锚定分 [0,1]：仅 cursor==0 时非零，(0,0) 满分。

    输出:
        (0,0)→1.0；曼哈顿距离越远按 1/(1+x+y) 衰减。
    """
    if cursor != 0:
        return 0.0
    if x == 0 and y == 0:
        return 1.0
    return 1.0 / (1.0 + float(x + y))


def _imitation_score(
    x: int,
    y: int,
    w: int,
    h: int,
    card: dict[str, Any],
    cols: int,
    rows: int,
) -> float:
    """与设计稿专家 (x,y,w,h) 的曼哈顿距离分 [0,1]。

    输入:
        card: 含 expert_x/y/w/h；无 expert_x 时返回 0。
    逻辑:
        dist = |Δx|+|Δy|+|Δw|+|Δh|，归一化后 1-dist/norm。
    """
    ex, ey = card.get("expert_x"), card.get("expert_y")
    ew, eh = card.get("expert_w"), card.get("expert_h")
    if ex is None or ey is None:
        return 0.0
    dist = abs(x - int(ex)) + abs(y - int(ey))
    if ew is not None and eh is not None:
        dist += abs(w - int(ew)) + abs(h - int(eh))
    return max(0.0, 1.0 - dist / max(1.0, float(cols + rows + cols + rows)))


def _prev_adjacent_score(
    card: dict[str, Any],
    x: int,
    y: int,
    placed: list[dict[str, Any]],
) -> float:
    """与「上一张放置序号」卡片的邻接分 [0,1]。

    输入:
        placed[-1]: 按时间序的前一张卡。
    逻辑:
        - 共享一条边且有接触长度 → 0.55~1.0
        - 未贴边 → 按 gap² 快速衰减，gap≥3 约 0
    """
    if not placed:
        return 0.0

    prev = placed[-1]
    w, h = int(card["w"]), int(card["h"])
    right, bottom = x + w, y + h
    ox, oy = int(prev["x"]), int(prev["y"])
    ow, oh = int(prev["w"]), int(prev["h"])
    oright, obottom = ox + ow, oy + oh

    shared = 0
    if right == ox or oright == x:
        shared += _overlap(y, bottom, oy, obottom)
    if bottom == oy or obottom == y:
        shared += _overlap(x, right, ox, oright)

    if shared > 0:
        contact = min(1.0, shared / max(1.0, float(min(w, h, ow, oh))))
        return 0.55 + 0.45 * contact

    gap_x = max(0, max(ox - right, x - oright))
    gap_y = max(0, max(oy - bottom, y - obottom))
    gap = gap_x + gap_y
    if gap <= 0:
        return 0.0
    return max(0.0, 0.5 / (gap * gap))


def packability_penalty(
    packable: bool,
    penalty: float,
) -> float:
    """剩余卡贪心不可行时的负奖励。

    输入:
        packable: greedy_packable 返回值。
        penalty: 通常为负数（config.PACKABILITY_PENALTY）。
    输出:
        packable=True → 0；False → penalty。
    """
    return 0.0 if packable else penalty


def style_reward(
    card: dict[str, Any],
    x: int,
    y: int,
    placed: list[dict[str, Any]],
    *,
    cols: int,
    rows: int,
    cursor: int,
    total_cards: int,
    edge_weight: float,
    alignment_weight: float,
    parallel_weight: float,
    order_weight: float,
    origin_weight: float,
    imitation_weight: float,
    prev_adjacent_weight: float,
    similarity_threshold: float = 0.75,
) -> tuple[float, dict[str, float]]:
    """计算单步样式奖励（各子项 0~1 乘以对应权重后求和）。

    输入:
        card: 当前卡，含 agent 选定的 w/h（已写入 card["w"], card["h"]）。
        x, y: 锚点。
        placed: 本步之前已放的卡。
        *_weight: config 中样式系数。
        similarity_threshold: parallel 子项的尺寸相似门槛。
    输出:
        (total_style_reward, details_dict)。
        details 含 edge_contact, alignment, similar_parallel, reading_order,
        origin_anchor, imitation, prev_adjacent 等原始分（未乘权重）。
    逻辑:
        - 首卡：仅 order + origin + imitation（无 edge/alignment/parallel）。
        - 后续：遍历 placed 累计贴边、对齐、相似并列分，再加 order 等。
    """
    order = _reading_order_score(
        card,
        x,
        y,
        placed,
        cols=cols,
        rows=rows,
        cursor=cursor,
        total_cards=total_cards,
    )
    origin = _origin_anchor_score(x, y, cursor)
    w, h = int(card["w"]), int(card["h"])
    imitation = _imitation_score(x, y, w, h, card, cols, rows)
    prev_adjacent = _prev_adjacent_score(card, x, y, placed)

    if not placed:
        details = {
            "edge_contact": 0.0,
            "alignment": 0.0,
            "similar_parallel": 0.0,
            "reading_order": order,
            "origin_anchor": origin,
            "imitation": imitation,
            "prev_adjacent": 0.0,
        }
        return (
            order_weight * order
            + origin_weight * origin
            + imitation_weight * imitation
        ), details

    right, bottom = x + w, y + h
    shared_edge = 0
    alignment_scores: list[float] = []
    parallel_scores: list[float] = []

    for other in placed:
        ox, oy = int(other["x"]), int(other["y"])
        ow, oh = int(other["w"]), int(other["h"])
        oright, obottom = ox + ow, oy + oh

        horizontal_neighbor = right == ox or oright == x
        vertical_neighbor = bottom == oy or obottom == y

        vertical_edges_aligned = x == ox or right == oright
        horizontal_edges_aligned = y == oy or bottom == obottom
        alignment_scores.append(
            (float(vertical_edges_aligned) + float(horizontal_edges_aligned)) / 2.0
        )

        if horizontal_neighbor:
            shared_edge += _overlap(y, bottom, oy, obottom)
        if vertical_neighbor:
            shared_edge += _overlap(x, right, ox, oright)

        similarity = _size_similarity(card, other)
        if similarity < similarity_threshold:
            continue

        if horizontal_neighbor and y == oy:
            parallel_scores.append(similarity)
        elif vertical_neighbor and x == ox:
            parallel_scores.append(similarity)

    edge_contact = min(1.0, shared_edge / max(1.0, float(w + h)))
    alignment = max(alignment_scores, default=0.0)
    similar_parallel = max(parallel_scores, default=0.0)
    details = {
        "edge_contact": edge_contact,
        "alignment": alignment,
        "similar_parallel": similar_parallel,
        "reading_order": order,
        "origin_anchor": origin,
        "imitation": imitation,
        "prev_adjacent": prev_adjacent,
    }
    total = (
        edge_weight * edge_contact
        + alignment_weight * alignment
        + parallel_weight * similar_parallel
        + order_weight * order
        + origin_weight * origin
        + imitation_weight * imitation
        + prev_adjacent_weight * prev_adjacent
    )
    return total, details


def success_reward(base: float, density_coef: float, density: float) -> float:
    """终局成功奖励：放满全部卡时一次性给予。

    输入:
        base: 固定成功分（REWARD_SUCCESS）。
        density_coef: 占用率系数（REWARD_DENSITY）。
        density: 画布占用率 [0,1]。
    输出:
        base + density_coef * density。
    """
    return base + density_coef * density


def fail_reward(penalty: float, leftover: int, total: int) -> float:
    """终局失败惩罚：按未放置卡比例缩放。

    输入:
        penalty: 负基数（REWARD_FAIL）。
        leftover: 剩余未放卡数。
        total: 本局总卡数。
    输出:
        penalty * (leftover / total)。
    """
    return penalty * (leftover / max(1, total))
