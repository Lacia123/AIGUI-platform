"""奖励入口：位置由环境确定；专家几何已从生效奖励中关闭。

env.step 把本步状态打进 ctx 后调用 compute_reward。
分项：
  - imitation：对齐专家 (w,h)；依赖专家，已从 REWARD_TERMS 注释
  - packability：按类型样例最小格估算后续可放性；当前已关闭
  - structure：开头 textCard 矮通栏
  - page_structure：终局按序列激活的结构分支（标题/聚类/侧栏/嵌套/少卡填满）
  - layout_wh：内容能否装进提议 w×h（不读专家；仍未接入）
  - logic：原点/贴边/同型尺寸（不读专家框；仍未接入）
  - terminal：空白率 + 未放完（不再给恒定完成奖）
"""

from __future__ import annotations

import math
from typing import Any, Callable

from .card_types import type_min_wh

# ---------------------------------------------------------------------------
# 专家模仿（仅训练）：仅监督模型可控的 (w,h)
# ---------------------------------------------------------------------------
# 每个 episode 的 imitation 总预算。单步会除以总 Card 数，避免长页面仅因
# Card 更多而获得数倍回报。
IMITATION_WEIGHT = 0
# 精确尺寸占主导，避免 3×1 对 5×1 仍拿到过多稠密分。
IMITATION_EXACT_MIX = 0.75
# L1 距离的指数塑形强度。IoU 不放进指数，避免 1×1 Card 只偏一格就几乎
# 丢失全部稠密奖励。
IMITATION_EXP_K = 4.0
# 有专家框时关闭 origin/adjacent/type-size 通用先验，避免贴边模板刷分。
LOGIC_ON_EXPERT_EPISODES = False

# ---------------------------------------------------------------------------
# 后续可放性：剩余卡按类型最小格，沿左上锚点是否还能放下
# ---------------------------------------------------------------------------
PACKABILITY_WEIGHT = 1.0
# 最小格已经按锚点放不下时，扣 PENALTY * remaining/N。
PACKABILITY_PENALTY = -16.0
# 剩余最小面积超过空格时，再按溢出面积 / 画布面积扣分。
PACKABILITY_AREA_WEIGHT = 20.0

# ---------------------------------------------------------------------------
# 结构先验。
# 开头 textCard：倾向矮通栏。showcase / targetStat 连续同型时跳过。
# ---------------------------------------------------------------------------
BAND_WIDTH_WEIGHT = 20.0
BAND_HEIGHT_WEIGHT = 12.0
BAND_MAX_H = 2
# 连续同型（run≥2）时更像拆行或铺瓷砖，不做通栏先验。textCard 不在此列。
BAND_SKIP_RUN_TYPES = frozenset({"showcaseCard", "targetStatCard"})
# 类型默认最小格。面积不够、丢掉横竖倾向、或胀得过大时扣分。
MIN_SIZE_WEIGHT = 8.0
EXPAND_WEIGHT = 2.0
EXPAND_AXIS_WEIGHT = 4.0
# 连续 targetStat / mistakes：同带、等分、封口；任意邻卡共边。
# 逐步邻卡对齐已关闭，改由终局整页结构分 page_structure_reward 负责。
ROW_ALIGN_TYPES = frozenset({"targetStatCard", "mistakesCard"})
ROW_ALIGN_WEIGHT = 2.0
ALIGN_EDGE_WEIGHT = 0.25
ALIGN_BAND_WEIGHT = 1.0
ALIGN_SPLIT_WEIGHT = 0.5
ALIGN_FLUSH_WEIGHT = 0.75
# 本卡最小面积 / 队列最小面积之和 × 画布格数，作为应占份额。
# 对目标上下偏差对称扣分；每张允许半格离散误差，整页总预算约为该权重。
AREA_SHARE_WEIGHT = 16.0
AREA_SHARE_TOLERANCE_CELLS = 0.5
# 终局整页结构：按当前序列激活的类型分支取均值（没有的类型不加这项）。
PAGE_STRUCTURE_WEIGHT = 16.0
TYPED_BAND_MIX = 0.25
NESTED_MIX = 0.25
ROW_COVER_MIX = 0.15
SPLIT_REUSE_MIX = 0.10
TYPE_SPLIT_MIX = 0.15
THIN_BANNER_MIX = 0.10
# 只有标题适合单独矮通栏；大卡 1 格高通栏、指标卡独自通栏都不算成行。
HEADER_BAND_TYPES = frozenset({"textCard"})
BLOCK_TYPES = frozenset(
    {
        "showcaseCard",
        "pairedImageTextCard",
        "heroCard",
        "contentSummaryCard",
    }
)
SPLIT_TYPES = frozenset({"targetStatCard", "mistakesCard"})
FILL_TYPES = frozenset(
    {
        "Topology",
        "__rawMarkdown__",
        "summaryCard",
        "[table:commonStyle]",
        "table",
    }
)
SIDEBAR_TYPES = BLOCK_TYPES | FILL_TYPES

# ---------------------------------------------------------------------------
# 终局：空白率 + 未放完；不再给恒定 +100（掩码已保证大多能放完）。
# ---------------------------------------------------------------------------
TERMINAL_SUCCESS = 0.0
TERMINAL_FULL_BONUS = 0.0
# 提前失败时按剩余 Card 比例计算的负分系数。
TERMINAL_FAIL = -16.0
# 终局空白率误差系数。
TERMINAL_BLANK_WEIGHT = 16.0

# ---------------------------------------------------------------------------
# 单卡内容 layout-check（只扣分；接口奖励暂不接入 REWARD_TERMS）
# ---------------------------------------------------------------------------
# layout-check 结果的整体缩放系数。
LAYOUT_WH_WEIGHT = 1.0
# PSUIP 内容装不进提议 w×h 时的基础负分；装得下不额外加分。
LAYOUT_WH_INVALID = -1.0

# ---------------------------------------------------------------------------
# 几何先验：原点 / 贴边 / 同型尺寸（弱于 imitation，避免刷分压过专家）
# ---------------------------------------------------------------------------
# 首张 Card 放在左上角 (0,0) 时的奖励。
LOGIC_ORIGIN_WEIGHT = 1.0
# 新 Card 与上一张 Card 共享边时的奖励。
LOGIC_ADJACENT_WEIGHT = 0.8
# 当前 Card 与之前同类型 Card 尺寸越相似，获得的奖励越高。
LOGIC_TYPE_SIZE_WEIGHT = 0.5
# 首张 Card 期望使用的画布原点，可按需要改成其他锚点。
FIRST_CARD_ORIGIN_XY = (0, 0)


RewardFn = Callable[[dict[str, Any]], tuple[float, dict[str, float]]]


def _expert_box(card: dict[str, Any] | None) -> tuple[int, int, int, int] | None:
    """读取当前卡的标注框 (x, y, w, h)；缺坐标则视为无标注。"""
    if not card:
        return None
    ex, ey = card.get("expert_x"), card.get("expert_y")
    ew, eh = card.get("expert_w"), card.get("expert_h")
    if ex is None or ey is None or ew is None or eh is None:
        return None
    return int(ex), int(ey), int(ew), int(eh)


def _expert_size(card: dict[str, Any] | None) -> tuple[int, int] | None:
    """读取专家尺寸；位置缺失时仍可用于尺寸监督。"""
    if not card:
        return None
    ew, eh = card.get("expert_w"), card.get("expert_h")
    if ew is None or eh is None:
        return None
    return int(ew), int(eh)


def annotation_xy_error(
    x: int,
    y: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """计算预测位置相对专家位置的归一化误差，范围 [0, 1]。

    x/y 分别按各自合法跨度归一化，只平均存在自由度的轴。这样横纵轴同权，
    且在 1 列或 1 行画布上不会让固定轴稀释另一轴的误差。完全重合为 0。
    """
    box = _expert_box(card)
    if box is None:
        return 1.0
    ex, ey, _ew, _eh = box
    errors: list[float] = []
    if cols > 1:
        errors.append(abs(x - ex) / float(cols - 1))
    if rows > 1:
        errors.append(abs(y - ey) / float(rows - 1))
    return max(0.0, min(1.0, sum(errors) / len(errors))) if errors else 0.0


def annotation_wh_error(
    w: int,
    h: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """计算预测尺寸相对专家尺寸的归一化误差，范围 [0, 1]。

    w/h 的合法范围分别为 1..cols 和 1..rows，所以最大变化跨度是 cols-1
    和 rows-1。只平均存在尺寸自由度的轴，完全一致为 0。
    """
    size = _expert_size(card)
    if size is None:
        return 1.0
    ew, eh = size
    errors: list[float] = []
    if cols > 1:
        errors.append(abs(w - ew) / float(cols - 1))
    if rows > 1:
        errors.append(abs(h - eh) / float(rows - 1))
    return max(0.0, min(1.0, sum(errors) / len(errors))) if errors else 0.0


def annotation_xy_score(
    x: int,
    y: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """位置接近度 = 1 - 位置误差。"""
    return 1.0 - annotation_xy_error(x, y, card, cols, rows)


def annotation_wh_score(
    w: int,
    h: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """尺寸接近度 = 1 - 尺寸误差。"""
    return 1.0 - annotation_wh_error(w, h, card, cols, rows)


def annotation_l1_error(
    x: int,
    y: int,
    w: int,
    h: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """兼容旧评估字段；固定位置动作下仅返回尺寸误差。"""
    return annotation_wh_error(w, h, card, cols, rows)


def annotation_l1_score(
    x: int,
    y: int,
    w: int,
    h: int,
    card: dict[str, Any] | None,
    cols: int,
    rows: int,
) -> float:
    """四维框接近度 = 1 - L1 误差。"""
    return 1.0 - annotation_l1_error(x, y, w, h, card, cols, rows)


def annotation_iou_score(
    x: int,
    y: int,
    w: int,
    h: int,
    card: dict[str, Any] | None,
) -> float:
    """预测矩形和专家矩形的交并比 IoU，范围 [0, 1]。

    ``IoU = 交集面积 / 并集面积``。完全重合为 1，不相交为 0。它能严格
    衡量完整框匹配质量，但两个框不相交时无法表达距离远近。
    """
    box = _expert_box(card)
    if box is None or w <= 0 or h <= 0:
        return 0.0
    ex, ey, ew, eh = box
    if ew <= 0 or eh <= 0:
        return 0.0
    inter_w = max(0, min(x + w, ex + ew) - max(x, ex))
    inter_h = max(0, min(y + h, ey + eh) - max(y, ey))
    inter = inter_w * inter_h
    union = w * h + ew * eh - inter
    if union <= 0:
        return 0.0
    return inter / float(union)


def annotation_wh_iou_score(
    w: int,
    h: int,
    card: dict[str, Any] | None,
) -> float:
    """忽略位置后的尺寸矩形 IoU，衡量模型实际可控的宽高。"""
    size = _expert_size(card)
    if size is None or w <= 0 or h <= 0:
        return 0.0
    ew, eh = size
    inter = min(w, ew) * min(h, eh)
    union = w * h + ew * eh - inter
    return inter / float(union) if union > 0 else 0.0


def imitation_exp_from_error(error: float, k: float = IMITATION_EXP_K) -> float:
    """按归一化误差做归一化指数衰减，映射到 [0, 1]。

    ``shaped = (exp(-k*error) - exp(-k)) / (1 - exp(-k))``

    - error=0 → 1（满分）
    - error=1 → 0（最差不再残留正奖励）
    - k 越大，只有非常接近专家框时才有明显奖励
    """
    error = max(0.0, min(1.0, float(error)))
    k = max(1e-6, float(k))
    floor = math.exp(-k)
    return (math.exp(-k * error) - floor) / (1.0 - floor)


def annotation_exact_hit(
    x: int,
    y: int,
    w: int,
    h: int,
    card: dict[str, Any] | None,
) -> bool:
    """预测尺寸是否与专家 (w,h) 完全一致；x/y 参数仅为接口兼容。"""
    size = _expert_size(card)
    if size is None:
        return False
    ew, eh = size
    return w == ew and h == eh


def imitation_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """奖励 1：只监督尺寸，精确命中为主、尺寸 IoU 提供稠密坡度。"""
    empty = {
        "imitation": 0.0,
        "annotation_xy": 0.0,
        "annotation_wh": 0.0,
        "annotation_l1": 0.0,
        "annotation_iou": 0.0,
        "annotation_error": 1.0,
        "annotation_distance_shaped": 0.0,
        "annotation_shaped": 0.0,
        "annotation_hit": 0.0,
        "annotation_miss": 0.0,
    }
    if not ctx.get("valid"):
        return 0.0, empty
    if _expert_size(ctx.get("card")) is None:
        return 0.0, empty

    card = ctx.get("card")
    x, y, w, h = int(ctx["x"]), int(ctx["y"]), int(ctx["w"]), int(ctx["h"])
    cols, rows = int(ctx["cols"]), int(ctx["rows"])

    xy = annotation_xy_score(x, y, card, cols, rows)
    wh = annotation_wh_score(w, h, card, cols, rows)
    l1 = annotation_l1_score(x, y, w, h, card, cols, rows)
    box_err = annotation_wh_error(w, h, card, cols, rows)
    iou = annotation_wh_iou_score(w, h, card)
    distance_shaped = imitation_exp_from_error(box_err)

    total_cards = max(1, int(ctx.get("total_cards") or 1))
    hit = annotation_exact_hit(x, y, w, h, card)
    exact_mix = min(1.0, max(0.0, IMITATION_EXACT_MIX))
    shaped = exact_mix * float(hit) + (1.0 - exact_mix) * iou
    reward = IMITATION_WEIGHT * shaped / total_cards
    miss = 0.0
    return reward, {
        "imitation": reward,
        "annotation_xy": xy,
        "annotation_wh": wh,
        "annotation_l1": l1,
        "annotation_iou": iou,
        "annotation_error": box_err,
        "annotation_distance_shaped": distance_shaped,
        "annotation_shaped": shaped,
        "annotation_hit": 1.0 if hit else 0.0,
        "annotation_miss": miss,
    }


def blank_ratio(ctx: dict[str, Any]) -> float:
    """计算画布空白格比例，供终局奖励使用。

    例如 5×3 画布共 15 格，Card 占用 9 格，则 blank_ratio = 6/15 = 0.4。
    """
    cols = max(1, int(ctx.get("cols") or 1))
    rows = max(1, int(ctx.get("rows") or 1))
    dens = ctx.get("density")
    if dens is not None:
        return max(0.0, min(1.0, 1.0 - float(dens)))
    occ = ctx.get("occupancy")
    if occ is None:
        return 1.0
    filled = float(occ[:rows, :cols].sum())
    return max(0.0, min(1.0, 1.0 - filled / float(cols * rows)))


def leftover_ratio(ctx: dict[str, Any]) -> float:
    """计算未放置 Card 比例，供失败终局惩罚使用。

    例如共有 10 张 Card，只放置 6 张，则 leftover_ratio = 0.4。
    """
    total = max(1, int(ctx.get("total_cards") or 1))
    placed_n = int(ctx.get("cursor") or 0)
    return max(0.0, (total - placed_n) / float(total))


def terminal_success_reward(blank_error: float) -> float:
    """成功终局：按空白率扣分；填满时该项为 0。

    不再给恒定完成奖。专家空白率目标已关闭，目标固定为 0。
    """
    full_bonus = TERMINAL_FULL_BONUS if blank_error <= 1e-9 else 0.0
    return (
        TERMINAL_SUCCESS
        + full_bonus
        - TERMINAL_BLANK_WEIGHT * blank_error
    )


def terminal_fail_penalty(leftover: float, blank_error: float) -> float:
    """失败终局：同时惩罚未放 Card 和相对目标的空白率误差。

    当前公式为 ``TERMINAL_FAIL * leftover - TERMINAL_BLANK_WEIGHT * blank_error``。
    """
    return TERMINAL_FAIL * leftover - TERMINAL_BLANK_WEIGHT * blank_error


def terminal_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """奖励 2：终局完整性与空间利用率奖励。

    普通中间步骤返回 0。只有环境 ``terminated`` 或 ``truncated`` 时计算：

    - 成功放完：完成奖减去相对目标空白率的差异；
    - 提前失败：额外按未放 Card 比例扣分。

    专家空白率目标已关闭，目标固定为 0（鼓励填满）。
    """
    blank = blank_ratio(ctx)
    leftover = leftover_ratio(ctx)
    # 专家空白率目标已关闭：
    # expert_blank = ctx.get("expert_blank_ratio")
    # target_blank = (
    #     max(0.0, min(1.0, float(expert_blank)))
    #     if expert_blank is not None
    #     else 0.0
    # )
    target_blank = 0.0
    blank_error = abs(blank - target_blank)
    details = {
        "terminal": 0.0,
        "terminal_full_bonus": 0.0,
        "blank_ratio": blank,
        "expert_blank_ratio": target_blank,
        "blank_error": blank_error,
        "leftover_ratio": leftover,
        "fill_ratio": 1.0 - blank,
    }
    if not ctx.get("terminated") and not ctx.get("truncated"):
        return 0.0, details

    finished = bool(ctx.get("terminated")) and leftover <= 0.0
    if finished and blank_error <= 1e-9:
        details["terminal_full_bonus"] = TERMINAL_FULL_BONUS
    reward = (
        terminal_success_reward(blank_error)
        if finished
        else terminal_fail_penalty(leftover, blank_error)
    )
    details["terminal"] = reward
    return reward, details


def layout_wh_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """可选奖励 3：检查 Card 内容能否装入模型提议的 w×h。

    该项把 Card 的裸 PSUIP 发给 ``layout-check`` 服务：

    - 内容装得下：奖励 0；
    - 内容装不下：当前扣 1 分；
    - 服务不可达、无 PSUIP 或动作非法：奖励 0，不影响训练。

    这是只惩罚、不奖励的约束项。目前没有加入 ``REWARD_TERMS``，因此相关
    常量和 HTTP 配置即使开启也不会实际改变总奖励。
    """
    details = {
        "layout_wh": 0.0,
        "layout_wh_valid": 0.0,
        "layout_wh_reachable": 0.0,
    }
    if not ctx.get("valid"):
        return 0.0, details
    card = ctx.get("card") or {}
    psuip = str(card.get("psuip") or "").strip()
    if not psuip:
        return 0.0, details

    from .layout_check import check_layout

    w, h = int(ctx["w"]), int(ctx["h"])
    result = check_layout(psuip, w, h)
    reachable = bool(result.get("reachable"))
    details["layout_wh_reachable"] = 1.0 if reachable else 0.0
    if not reachable or result.get("valid") is None:
        return 0.0, details

    ok = bool(result["valid"])
    details["layout_wh_valid"] = 1.0 if ok else 0.0
    reward = 0.0 if ok else LAYOUT_WH_WEIGHT * LAYOUT_WH_INVALID
    details["layout_wh"] = reward
    return reward, details


def _card_type_min_wh(card: dict[str, Any] | None) -> tuple[int, int] | None:
    """按类型查默认最小格。未知类型返回 None，调用方保持中性。"""
    typ = str((card or {}).get("type") or "")
    return type_min_wh(typ)


def _anchored_min_packable(
    occ: Any,
    remaining: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> bool | None:
    """剩余卡各取类型最小格，按环境左上锚点顺序能否放下。"""
    from .layout import anchored_box, can_place, place, top_left_empty_anchor

    board = occ.copy()
    for card in remaining:
        wh = _card_type_min_wh(card)
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


def packability_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """惩罚当前放置把剩余卡的最小格挤没的动作。

    不读专家尺寸。任一剩余卡没有类型默认格时整项中性。
    """
    details = {
        "packability": 0.0,
        "packability_ok": 1.0,
        "packability_area": 0.0,
    }
    if not ctx.get("valid"):
        return 0.0, details

    remaining = list(ctx.get("remaining") or [])
    if not remaining:
        return 0.0, details

    occ = ctx.get("occupancy")
    cols = int(ctx["cols"])
    rows = int(ctx["rows"])
    if occ is None:
        return 0.0, details

    needed = 0
    for card in remaining:
        wh = _card_type_min_wh(card)
        if wh is None:
            return 0.0, details
        needed += int(wh[0]) * int(wh[1])
    free = int(cols * rows - int(occ[:rows, :cols].sum()))
    overflow = max(0, needed - free)
    if overflow:
        details["packability_area"] = (
            -PACKABILITY_AREA_WEIGHT * overflow / float(max(1, cols * rows))
        )

    ok = _anchored_min_packable(occ, remaining, cols, rows)
    if ok is None:
        return 0.0, details
    details["packability_ok"] = 1.0 if ok else 0.0
    total_cards = max(1, int(ctx.get("total_cards") or 1))
    leftover_n = len(remaining) / float(total_cards)
    reward = float(details["packability_area"])
    if not ok:
        reward += PACKABILITY_WEIGHT * PACKABILITY_PENALTY * leftover_n
    details["packability"] = reward
    return reward, details


def _consecutive_run_len(ctx: dict[str, Any]) -> int:
    """当前卡起连续同类型张数（含自己；remaining 已不含当前卡）。"""
    typ = (ctx.get("card") or {}).get("type")
    n = 1
    if not typ:
        return n
    for card in ctx.get("remaining") or []:
        if card.get("type") == typ:
            n += 1
        else:
            break
    return n


def structure_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """首张后面还有卡时倾向通栏。textCard 即使后面还是 text 也计入。

    showcase / targetStat 连续同型时跳过，避免宫格和 KPI 行被拉成通栏。
    """
    details = {
        "structure": 0.0,
        "structure_band": 0.0,
        "structure_width_n": 0.0,
    }
    if not ctx.get("valid"):
        return 0.0, details
    placed = ctx.get("placed") or []
    if len(placed) != 1 or not (ctx.get("remaining") or []):
        return 0.0, details
    typ = str((ctx.get("card") or {}).get("type") or "")
    run = _consecutive_run_len(ctx)
    if run != 1 and typ in BAND_SKIP_RUN_TYPES:
        return 0.0, details
    cols = max(1, int(ctx["cols"]))
    rows = max(1, int(ctx.get("rows") or 1))
    w = int(ctx["w"])
    h = int(ctx.get("h") or 1)
    width_n = w / float(cols)
    details["structure_width_n"] = width_n
    details["structure_band"] = 1.0 if w == cols else 0.0
    reward = BAND_WIDTH_WEIGHT * (width_n - 0.85)
    if typ == "textCard":
        extra_h = max(0, h - BAND_MAX_H)
        if extra_h:
            reward -= BAND_HEIGHT_WEIGHT * extra_h / float(rows)
    details["structure"] = reward
    return reward, details


def _shape_tendency_gap(w: int, h: int, min_w: int, min_h: int) -> float:
    """放大时保持最小格的长短边方向。正方形不限制方向。

    最小格列大于行时，放置也要列大于行；行大于列时同理。
    变成正方形扣一半，方向对调扣满。
    """
    if min_w == min_h or w <= 0 or h <= 0:
        return 0.0
    if min_w > min_h:
        if w > h:
            return 0.0
        return 0.5 if w == h else 1.0
    if h > w:
        return 0.0
    return 0.5 if h == w else 1.0


def min_size_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """面积不小于默认面积，并保持最小格的横竖倾向。

    正方形（如 3×3）可往任意方向放大，4×2 与 3×3 只差 1 格时仍算达标。
    1×2 这种高大于宽的，放大后也要行大于列。达到后奖励为 0。
    """
    details = {
        "min_size": 0.0,
        "min_size_ok": 1.0,
        "min_area_ratio": 1.0,
    }
    if not ctx.get("valid"):
        return 0.0, details
    typ = str((ctx.get("card") or {}).get("type") or "")
    minimum = type_min_wh(typ)
    if minimum is None:
        return 0.0, details
    min_w, min_h = minimum
    w, h = int(ctx["w"]), int(ctx["h"])
    min_area = max(1, min_w * min_h)
    placed_area = max(0, w) * max(0, h)
    area_ratio = placed_area / float(min_area)
    short_cells = max(0, min_area - placed_area - 1)
    gap = max(short_cells / float(min_area), _shape_tendency_gap(w, h, min_w, min_h))
    cols = max(1, int(ctx.get("cols") or 8))
    rows = max(1, int(ctx.get("rows") or 5))
    extra = max(0, placed_area - min_area - 1)
    expand_area = extra / float(cols * rows)
    if min_w > min_h:
        expand_axis = max(0, h - min_h) / float(rows)
    elif min_h > min_w:
        expand_axis = max(0, w - min_w) / float(cols)
    else:
        expand_axis = 0.0
    reward = (
        -MIN_SIZE_WEIGHT * gap
        - EXPAND_WEIGHT * expand_area
        - EXPAND_AXIS_WEIGHT * expand_axis
    )
    details["min_area_ratio"] = area_ratio
    details["min_size_ok"] = 1.0 if gap <= 0.0 else 0.0
    details["min_size"] = reward
    return reward, details


def _sequence_min_areas(
    ctx: dict[str, Any],
) -> tuple[int, int] | None:
    """当前卡最小面积，以及整页队列最小面积之和。缺类型时返回 None。"""
    cards = list(ctx.get("placed") or []) + list(ctx.get("remaining") or [])
    if not cards:
        return None
    areas: list[int] = []
    for card in cards:
        wh = _card_type_min_wh(card)
        if wh is None:
            return None
        areas.append(max(1, int(wh[0]) * int(wh[1])))
    current = _card_type_min_wh(ctx.get("card"))
    if current is None:
        return None
    return max(1, current[0] * current[1]), sum(areas)


def area_share_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """对称约束当前 Card 占整页的面积份额。

    份额 = 本卡最小面积 / 整页最小面积之和 × 画布格数。
    实际面积无论高于或低于目标都会按相对误差扣分，仅容忍半格离散误差。
    单卡惩罚除以 Card 总数，使不同长度页面的整页奖励量级稳定。
    """
    details = {
        "area_share": 0.0,
        "area_share_target": 0.0,
        "area_share_ratio": 1.0,
        "area_share_ok": 1.0,
    }
    if not ctx.get("valid"):
        return 0.0, details
    mins = _sequence_min_areas(ctx)
    if mins is None:
        return 0.0, details
    min_area, seq_area = mins
    cols = max(1, int(ctx.get("cols") or 1))
    rows = max(1, int(ctx.get("rows") or 1))
    page = float(cols * rows)
    share = (min_area / float(max(1, seq_area))) * page
    w, h = int(ctx["w"]), int(ctx["h"])
    placed_area = max(0, w) * max(0, h)
    cell_error = abs(placed_area - share)
    area_gap = max(0.0, cell_error - AREA_SHARE_TOLERANCE_CELLS) / max(
        share,
        1.0,
    )
    total_cards = max(1, int(ctx.get("total_cards") or len(
        list(ctx.get("placed") or []) + list(ctx.get("remaining") or [])
    )))
    reward = -AREA_SHARE_WEIGHT * area_gap / float(total_cards)
    details["area_share_target"] = share
    details["area_share_ratio"] = placed_area / share if share > 0 else 1.0
    details["area_share_ok"] = 1.0 if area_gap <= 0.0 else 0.0
    details["area_share"] = reward
    return reward, details


def _run_left(ctx: dict[str, Any]) -> int:
    """当前卡加后面连续同类型的张数。"""
    return _consecutive_run_len(ctx)


def _span_taken_and_available(
    occ: Any,
    x: int,
    y: int,
    w: int,
    h: int,
    cols: int,
    rows: int,
    axis: str,
) -> tuple[int, int]:
    """本卡已用跨度，以及锚点起仍空着的总跨度（含本卡）。occ 已含本卡。"""
    if axis == "x":
        extra = 0
        if occ is not None:
            xx = x + w
            while xx < cols and not occ[y : y + h, xx].any():
                extra += 1
                xx += 1
        return w, w + extra
    extra = 0
    if occ is not None:
        yy = y + h
        while yy < rows and not occ[yy, x : x + w].any():
            extra += 1
            yy += 1
    return h, h + extra


def _shape_ready(typ: str, w: int, h: int) -> bool:
    minimum = type_min_wh(typ)
    if minimum is None:
        return True
    min_w, min_h = minimum
    if w * h + 1 < min_w * min_h:
        return False
    return _shape_tendency_gap(w, h, min_w, min_h) <= 0.0


def row_align_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """结构对齐：所有连续 Card 成行/成列，同类指标卡再等分和封口。

    同行要求 y 与 h 相同，同列要求 x 与 w 相同，且矩形必须共享边。
    单纯共边只有弱奖励；targetStat / mistakes 额外走同带等分和封口。
    """
    details = {
        "row_align": 0.0,
        "row_align_ok": 0.0,
        "align_edge": 0.0,
        "align_split": 0.0,
        "align_flush": 0.0,
    }
    if not ctx.get("valid"):
        return 0.0, details
    typ = str((ctx.get("card") or {}).get("type") or "")
    x, y = int(ctx.get("x") or 0), int(ctx.get("y") or 0)
    w, h = int(ctx["w"]), int(ctx["h"])
    cols = max(1, int(ctx.get("cols") or 1))
    rows = max(1, int(ctx.get("rows") or 1))
    placed = ctx.get("placed") or []
    occ = ctx.get("occupancy")
    ready = _shape_ready(typ, w, h)

    prev = placed[-2] if len(placed) >= 2 else None
    band_axis = None
    if ready and prev:
        touching = _rectangles_share_edge(x, y, w, h, prev)
        if touching:
            details["align_edge"] = ALIGN_EDGE_WEIGHT
            same_y = y == int(prev["y"])
            same_x = x == int(prev["x"])
            same_h = h == int(prev["h"])
            same_w = w == int(prev["w"])
            if same_y and same_h:
                band_axis = "x"
            elif same_x and same_w:
                band_axis = "y"
            if band_axis:
                details["row_align_ok"] = 1.0
                details["row_align"] = ALIGN_BAND_WEIGHT

    run_left = _run_left(ctx)
    axis = None
    if typ in ROW_ALIGN_TYPES and ready:
        prev_same = bool(prev) and str(prev.get("type") or "") == typ
        if prev_same:
            axis = band_axis
            same_y = y == int(prev["y"])
            same_h = h == int(prev["h"])
            if not axis and same_y and not same_h:
                details["row_align"] = -0.5 * ALIGN_BAND_WEIGHT
        else:
            axis = "x"

        if axis and ctx.get("cols") is not None:
            taken, avail = _span_taken_and_available(
                occ, x, y, w, h, cols, rows, axis
            )
            if occ is None:
                avail = (cols - x) if axis == "x" else (rows - y)
                taken = w if axis == "x" else h
            ideal = avail / float(max(1, run_left))
            if abs(taken - ideal) <= 1.0:
                details["align_split"] = ALIGN_SPLIT_WEIGHT
            if run_left == 1 and taken == avail:
                details["align_flush"] = ALIGN_FLUSH_WEIGHT

    return (
        float(details["align_edge"])
        + float(details["row_align"])
        + float(details["align_split"])
        + float(details["align_flush"])
    ), details


def _size_similarity(w1: int, h1: int, w2: int, h2: int) -> float:
    """计算两张 Card 尺寸的相对相似度，范围 [0, 1]。

    宽、高差分别除以两者较大值后取平均，完全同尺寸为 1。
    """
    dw = abs(w1 - w2) / max(1, max(w1, w2))
    dh = abs(h1 - h2) / max(1, max(h1, h2))
    return max(0.0, 1.0 - 0.5 * (dw + dh))


def same_type_size_score(ctx: dict[str, Any]) -> float:
    """当前 Card 与全部已放同类型 Card 的平均尺寸相似度。

    该分数鼓励同一页面中的同类型 Card 使用相近尺寸。没有已放同类型 Card
    时返回 0，不会为了首张该类型 Card 凭空加分。
    """
    card = ctx.get("card") or {}
    type_ = card.get("type")
    if not type_:
        return 0.0
    w, h = int(ctx["w"]), int(ctx["h"])
    others = [
        p for p in (ctx.get("placed") or [])[:-1] if p.get("type") == type_
    ]
    if not others:
        return 0.0
    sims = [_size_similarity(w, h, int(p["w"]), int(p["h"])) for p in others]
    return sum(sims) / len(sims)


def first_card_origin_score(ctx: dict[str, Any]) -> float:
    """首张 Card 位于指定原点时为 1，否则为 0。

    只有 ``placed`` 中恰好有一张 Card 时计算，后续 Card 不重复获得该奖励。
    """
    placed = ctx.get("placed") or []
    if len(placed) != 1:
        return 0.0
    ox, oy = FIRST_CARD_ORIGIN_XY
    return 1.0 if int(ctx["x"]) == ox and int(ctx["y"]) == oy else 0.0


def _rectangles_share_edge(
    x: int,
    y: int,
    w: int,
    h: int,
    other: dict[str, Any],
) -> bool:
    """两个矩形是否共享一段长度大于 0 的水平边或垂直边。"""
    ox, oy = int(other["x"]), int(other["y"])
    ow, oh = int(other["w"]), int(other["h"])
    overlap_x = min(x + w, ox + ow) - max(x, ox)
    overlap_y = min(y + h, oy + oh) - max(y, oy)
    vertical = (x + w == ox or ox + ow == x) and overlap_y > 0
    horizontal = (y + h == oy or oy + oh == y) and overlap_x > 0
    return vertical or horizontal


def adjacent_placement_score(ctx: dict[str, Any]) -> float:
    """当前 Card 与上一张已放 Card 共享一段有效边时为 1。

    只检查队列中的前一张，不与更早的卡贴边计分，避免跳着补洞也算整齐。
    碰撞和越界已由 action mask 处理；仅角点接触不计为贴边。首张无上一张，得 0。
    """
    placed = ctx.get("placed") or []
    if len(placed) < 2:
        return 0.0
    prev = placed[-2]
    x, y = int(ctx["x"]), int(ctx["y"])
    w, h = int(ctx["w"]), int(ctx["h"])
    return 1.0 if _rectangles_share_edge(x, y, w, h, prev) else 0.0


def logic_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """奖励 5：与专家标注无关的通用几何先验。

    有专家框且 LOGIC_ON_EXPERT_EPISODES=False 时整项关闭，避免贴边/原点
    模板刷分压过专家布局。无专家（如 random）时才启用：

    - 同类型尺寸：最高 ``LOGIC_TYPE_SIZE_WEIGHT``；
    - 首卡位于原点：最高 ``LOGIC_ORIGIN_WEIGHT``；
    - 当前 Card 与上一张 Card 共享边：最高 ``LOGIC_ADJACENT_WEIGHT``。
    """
    type_size = first_origin = adjacent = 0.0
    # 专家门控已关闭：有标注时不再整项关掉。
    # has_expert = _expert_size(ctx.get("card")) is not None
    # allow_logic = (not has_expert) or LOGIC_ON_EXPERT_EPISODES
    allow_logic = True
    if ctx.get("valid") and allow_logic:
        type_size = same_type_size_score(ctx)
        first_origin = first_card_origin_score(ctx)
        adjacent = adjacent_placement_score(ctx)
    reward = (
        LOGIC_TYPE_SIZE_WEIGHT * type_size
        + LOGIC_ORIGIN_WEIGHT * first_origin
        + LOGIC_ADJACENT_WEIGHT * adjacent
    )
    return reward, {
        "logic": reward,
        "logic_type_size": type_size,
        "logic_origin": first_origin,
        "logic_adjacent": adjacent,
    }


def _row_band_groups(
    placed: list[dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """按 (y, h) 把已放卡分成水平带。"""
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for card in placed:
        key = (int(card["y"]), int(card["h"]))
        groups.setdefault(key, []).append(card)
    return groups


def _band_covers_width(cards: list[dict[str, Any]], cols: int) -> bool:
    """同一水平带内的卡是否无缝铺满 [0, cols)。"""
    if not cards:
        return False
    intervals = sorted(
        (int(card["x"]), int(card["x"]) + int(card["w"])) for card in cards
    )
    if intervals[0][0] != 0:
        return False
    cursor = 0
    for start, end in intervals:
        if start != cursor or end <= start:
            return False
        cursor = end
    return cursor == cols


def _card_type_name(card: dict[str, Any]) -> str:
    return str(card.get("type") or "")


def _rect(card: dict[str, Any]) -> tuple[int, int, int, int]:
    return (int(card["x"]), int(card["y"]), int(card["w"]), int(card["h"]))


def _through_cuts(
    cards: list[dict[str, Any]],
    box: tuple[int, int, int, int],
    axis: str,
) -> list[int]:
    """区域内部、不切开任何卡片的贯通分割线。"""
    bx, by, bw, bh = box
    edges: set[int] = set()
    if axis == "v":
        lo, hi = bx, bx + bw
        for card in cards:
            x, _y, w, _h = _rect(card)
            if x > lo:
                edges.add(x)
            if x + w < hi:
                edges.add(x + w)
        cuts = []
        for cut in sorted(edges):
            if all(_rect(card)[0] + _rect(card)[2] <= cut or _rect(card)[0] >= cut for card in cards):
                cuts.append(cut)
        return cuts
    lo, hi = by, by + bh
    for card in cards:
        _x, y, _w, h = _rect(card)
        if y > lo:
            edges.add(y)
        if y + h < hi:
            edges.add(y + h)
    cuts = []
    for cut in sorted(edges):
        if all(_rect(card)[1] + _rect(card)[3] <= cut or _rect(card)[1] >= cut for card in cards):
            cuts.append(cut)
    return cuts


def _split_box(
    cards: list[dict[str, Any]],
    box: tuple[int, int, int, int],
    axis: str,
    cuts: list[int],
) -> list[tuple[tuple[int, int, int, int], list[dict[str, Any]]]]:
    bx, by, bw, bh = box
    bounds = ([bx] + cuts + [bx + bw]) if axis == "v" else ([by] + cuts + [by + bh])
    parts: list[tuple[tuple[int, int, int, int], list[dict[str, Any]]]] = []
    for start, end in zip(bounds, bounds[1:]):
        if end <= start:
            continue
        if axis == "v":
            child = (start, by, end - start, bh)
            owned = [
                card
                for card in cards
                if _rect(card)[0] >= start and _rect(card)[0] + _rect(card)[2] <= end
            ]
        else:
            child = (bx, start, bw, end - start)
            owned = [
                card
                for card in cards
                if _rect(card)[1] >= start and _rect(card)[1] + _rect(card)[3] <= end
            ]
        parts.append((child, owned))
    return parts


def _parse_slice(
    cards: list[dict[str, Any]],
    box: tuple[int, int, int, int],
) -> dict[str, Any]:
    """把区域内的卡解析成行/列嵌套剖分（手工页的侧栏+指标行+列内再切）。"""
    directions: set[str] = set()
    groups: list[tuple[str, tuple[int, int, int, int], list[dict[str, Any]]]] = []

    def walk(
        owned: list[dict[str, Any]],
        region: tuple[int, int, int, int],
    ) -> bool:
        if not owned:
            return False
        if len(owned) == 1:
            x, y, w, h = _rect(owned[0])
            return (x, y, w, h) == region
        v_cuts = _through_cuts(owned, region, "v")
        h_cuts = _through_cuts(owned, region, "h")
        for axis, cuts in (("h", h_cuts), ("v", v_cuts)):
            if not cuts:
                continue
            parts = _split_box(owned, region, axis, cuts)
            if len(parts) < 2:
                continue
            saved_dirs = set(directions)
            saved_groups = len(groups)
            directions.add(axis)
            exact_leaves = [
                child_cards[0]
                for child, child_cards in parts
                if len(child_cards) == 1 and _rect(child_cards[0]) == child
            ]
            if exact_leaves:
                groups.append((axis, region, exact_leaves))
            if all(walk(child_cards, child) for child, child_cards in parts):
                return True
            directions.clear()
            directions.update(saved_dirs)
            del groups[saved_groups:]
        return False

    ok = walk(cards, box)
    return {
        "ok": ok,
        "bidirectional": int("v" in directions and "h" in directions),
        "directions": directions,
        "groups": groups,
    }


def _typed_credit_in_group(
    card: dict[str, Any],
    siblings: list[dict[str, Any]],
    axis: str,
    box: tuple[int, int, int, int],
    cols: int,
) -> float:
    """在剖分子区域里按类型给成行/成列分。"""
    typ = _card_type_name(card)
    _bx, _by, bw, _bh = box
    height = int(card["h"])
    width = int(card["w"])
    if len(siblings) >= 2:
        if axis == "v":
            return 1.0
        if bw < cols:
            return 1.0
        if (
            typ in SPLIT_TYPES
            and all(_card_type_name(item) == typ for item in siblings)
            and all(int(item["h"]) >= 2 for item in siblings)
        ):
            return 1.0
        # 整页通栏横条叠在一起：按单卡类型规则，不因为「多行」给满分。
    if typ in HEADER_BAND_TYPES:
        return 1.0 if width == cols and height <= 2 else 0.4
    if typ in BLOCK_TYPES:
        if height <= 1 and width == cols:
            return 0.0
        if width < cols and height >= 2:
            return 0.85
        return 0.55 if height >= 2 else 0.0
    if typ in SPLIT_TYPES:
        return 0.15
    if height <= 1 and width == cols:
        return 0.0
    if width < cols and height >= 2:
        return 0.7
    return 0.5 if height >= 2 else 0.0


def _typed_band_credit(
    card: dict[str, Any],
    band: list[dict[str, Any]],
    cols: int,
) -> float:
    """单卡的类型成行分：多卡切开满分；只有标题才奖单独矮通栏。"""
    if not _band_covers_width(band, cols):
        return 0.0
    if len(band) >= 2:
        return 1.0
    typ = _card_type_name(card)
    height = int(card["h"])
    if typ in HEADER_BAND_TYPES:
        return 1.0 if height <= 2 else 0.4
    if typ in BLOCK_TYPES:
        return 0.0 if height <= 1 else 0.55
    if typ in SPLIT_TYPES:
        return 0.15
    return 0.0 if height <= 1 else 0.5


def _band_counts_as_coverage(band: list[dict[str, Any]], cols: int) -> bool:
    """完整行带是否计入页面覆盖：切开、标题矮通栏、或有厚度的内容块。"""
    if not _band_covers_width(band, cols):
        return False
    if len(band) >= 2:
        return True
    card = band[0]
    typ = _card_type_name(card)
    height = int(card["h"])
    if typ in HEADER_BAND_TYPES:
        return height <= 2
    if typ in BLOCK_TYPES:
        return height >= 2
    if typ in SPLIT_TYPES:
        return False
    return height >= 2


def _same_type_split_score(
    placed: list[dict[str, Any]],
    cols: int,
    slice_groups: list[tuple[str, tuple[int, int, int, int], list[dict[str, Any]]]] | None = None,
) -> float:
    """指标卡是否在同一行带或同一列带里近似等分。没有指标卡时中性为 1。"""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for card in placed:
        typ = _card_type_name(card)
        if typ in SPLIT_TYPES:
            by_type.setdefault(typ, []).append(card)
    if not by_type:
        return 1.0
    member_sets: list[set[int]] = []
    if slice_groups:
        for axis, box, siblings in slice_groups:
            if len(siblings) < 2:
                continue
            bw = int(box[2])
            if axis == "v" or bw < cols:
                member_sets.append({id(card) for card in siblings})
                continue
            types = {_card_type_name(card) for card in siblings}
            if (
                len(types) == 1
                and next(iter(types)) in SPLIT_TYPES
                and all(int(card["h"]) >= 2 for card in siblings)
            ):
                member_sets.append({id(card) for card in siblings})
    row_groups = _row_band_groups(placed)
    for band in row_groups.values():
        if len(band) >= 2 and _band_covers_width(band, cols):
            member_sets.append({id(card) for card in band})
    col_groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for card in placed:
        col_groups.setdefault((int(card["x"]), int(card["w"])), []).append(card)
    for (x, width), band in col_groups.items():
        if len(band) < 2 or width >= cols:
            continue
        ordered = sorted(band, key=lambda item: int(item["y"]))
        cursor = int(ordered[0]["y"])
        contiguous = True
        for item in ordered:
            if int(item["y"]) != cursor:
                contiguous = False
                break
            cursor += int(item["h"])
        if contiguous:
            member_sets.append({id(card) for card in ordered})
    scores: list[float] = []
    for cards in by_type.values():
        if len(cards) < 2:
            scores.append(1.0)
            continue
        wanted = {id(card) for card in cards}
        matched = False
        similar = False
        for members in member_sets:
            if wanted <= members:
                matched = True
                widths = [int(card["w"]) for card in cards]
                heights = [int(card["h"]) for card in cards]
                similar = (
                    max(widths) - min(widths) <= 1
                    or max(heights) - min(heights) <= 1
                )
                break
        if matched:
            scores.append(1.0 if similar else 0.6)
        else:
            scores.append(0.0)
    return sum(scores) / len(scores)


def _split_reuse_score(
    groups: dict[tuple[int, int], list[dict[str, Any]]],
    cols: int,
) -> float:
    """只统计多卡完整行带的竖线。全是通栏横条时为 0，不再当满分。"""
    counts: dict[int, int] = {}
    split_bands = 0
    for band in groups.values():
        if not _band_covers_width(band, cols) or len(band) < 2:
            continue
        split_bands += 1
        for card in band:
            x = int(card["x"])
            right = x + int(card["w"])
            if x > 0:
                counts[x] = counts.get(x, 0) + 1
            if right < cols:
                counts[right] = counts.get(right, 0) + 1
    if split_bands == 0:
        return 0.0
    if not counts:
        return 0.0
    incidences = sum(counts.values())
    shared = sum(n_hit for n_hit in counts.values() if n_hit >= 2)
    return 0.7 + 0.3 * (shared / float(incidences))


def _cards_of(placed: list[dict[str, Any]], types: frozenset[str] | str) -> list[dict[str, Any]]:
    if isinstance(types, str):
        return [card for card in placed if _card_type_name(card) == types]
    return [card for card in placed if _card_type_name(card) in types]


def _is_first_header(card: dict[str, Any], placed: list[dict[str, Any]]) -> bool:
    return bool(placed) and card is placed[0] and _card_type_name(card) == "textCard"


def _header_branch(placed: list[dict[str, Any]], cols: int) -> float:
    if not placed or _card_type_name(placed[0]) != "textCard":
        return 1.0
    card = placed[0]
    width, height, y = int(card["w"]), int(card["h"]), int(card["y"])
    if width != cols:
        return 0.2
    if height <= 2 and y == 0:
        return 1.0
    if height <= 2:
        return 0.8
    return 0.4


def _cluster_branch(
    placed: list[dict[str, Any]],
    typ: str,
    cols: int,
    slice_groups: list[tuple[str, tuple[int, int, int, int], list[dict[str, Any]]]],
) -> float:
    cards = _cards_of(placed, typ)
    if len(cards) < 2:
        return 1.0
    if all(int(card["w"]) == cols and int(card["h"]) == 1 for card in cards):
        return 0.0
    wanted = {id(card) for card in cards}
    for axis, box, siblings in slice_groups:
        if wanted <= {id(card) for card in siblings} and len(siblings) >= 2:
            if axis == "v" or int(box[2]) < cols:
                widths = [int(card["w"]) for card in cards]
                heights = [int(card["h"]) for card in cards]
                if max(widths) - min(widths) <= 1 or max(heights) - min(heights) <= 1:
                    return 1.0
                return 0.6
            if (
                {_card_type_name(card) for card in siblings} == {typ}
                and all(int(card["h"]) >= 2 for card in cards)
            ):
                return 1.0
    xs = {(int(card["x"]), int(card["w"])) for card in cards}
    ys = {(int(card["y"]), int(card["h"])) for card in cards}
    if len(xs) == 1 and list(xs)[0][1] < cols:
        return 0.8
    if len(ys) == 1:
        return 0.7
    return 0.15


def _block_branch(placed: list[dict[str, Any]], cols: int) -> float:
    return _shape_group_score(_cards_of(placed, BLOCK_TYPES), cols, prefer_column=True)


def _fill_branch(placed: list[dict[str, Any]], cols: int) -> float:
    return _shape_group_score(_cards_of(placed, FILL_TYPES), cols, prefer_column=False)


def _shape_group_score(
    cards: list[dict[str, Any]],
    cols: int,
    prefer_column: bool,
) -> float:
    if not cards:
        return 1.0
    scores = []
    for card in cards:
        width, height = int(card["w"]), int(card["h"])
        if width == cols and height <= 1:
            scores.append(0.0)
        elif width < cols and height >= 2:
            scores.append(1.0)
        elif width == cols and height >= 2:
            scores.append(0.55 if prefer_column else 1.0)
        else:
            scores.append(0.4)
    return sum(scores) / len(scores)


def _sidebar_branch(placed: list[dict[str, Any]], cols: int, rows: int) -> float:
    del rows
    max_w = max(2, cols // 2)
    for card in _cards_of(placed, SIDEBAR_TYPES):
        x, width, height = int(card["x"]), int(card["w"]), int(card["h"])
        if width <= max_w and height >= 2 and (x == 0 or x + width == cols):
            return 1.0
    return 0.0


def _nested_branch(parsed: dict[str, Any], profile: dict[str, int]) -> float:
    if not parsed["ok"]:
        return 0.0
    complex_page = profile["n"] >= 5 or (
        profile["n_block"] >= 1
        and (profile["n_stat"] >= 2 or profile["n_mist"] >= 2)
    )
    if complex_page:
        return 1.0 if parsed["bidirectional"] else 0.35
    return 1.0


def _few_card_branch(
    placed: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> float:
    filled = sum(int(card["w"]) * int(card["h"]) for card in placed)
    fill = filled / float(max(1, cols * rows))
    tall = [
        card
        for card in placed
        if _card_type_name(card) not in HEADER_BAND_TYPES and int(card["h"]) >= 2
    ]
    if fill >= 0.85:
        return 1.0
    if tall:
        return 0.45 + 0.4 * fill
    return 0.2 * fill


def _no_thin_branch(placed: list[dict[str, Any]], cols: int) -> float:
    n = len(placed)
    if n == 0:
        return 1.0
    thin = sum(
        1
        for card in placed
        if int(card["w"]) == cols
        and int(card["h"]) == 1
        and not _is_first_header(card, placed)
    )
    return 1.0 - thin / float(n)


def _sequence_profile(placed: list[dict[str, Any]]) -> dict[str, int]:
    types = [_card_type_name(card) for card in placed]
    return {
        "n": len(types),
        "n_stat": types.count("targetStatCard"),
        "n_mist": types.count("mistakesCard"),
        "n_block": sum(1 for typ in types if typ in BLOCK_TYPES),
        "n_fill": sum(1 for typ in types if typ in FILL_TYPES),
        "has_header": int(bool(types) and types[0] == "textCard"),
    }


def _sequence_branch_scores(
    placed: list[dict[str, Any]],
    cols: int,
    rows: int,
    parsed: dict[str, Any],
    slice_groups: list[tuple[str, tuple[int, int, int, int], list[dict[str, Any]]]],
) -> dict[str, float]:
    """按当前序列激活的结构分支。没有的类型不加这项，避免硬套侧栏或通栏。"""
    profile = _sequence_profile(placed)
    scores: dict[str, float] = {
        "tile": 1.0 if parsed["ok"] else 0.2,
        "no_thin": _no_thin_branch(placed, cols),
    }
    if profile["has_header"]:
        scores["header"] = _header_branch(placed, cols)
    if profile["n_stat"] >= 2:
        scores["stat_cluster"] = _cluster_branch(
            placed, "targetStatCard", cols, slice_groups
        )
    if profile["n_mist"] >= 2:
        scores["mist_cluster"] = _cluster_branch(
            placed, "mistakesCard", cols, slice_groups
        )
    if profile["n_block"] >= 1:
        scores["block_shape"] = _block_branch(placed, cols)
    if profile["n_fill"] >= 1:
        scores["fill_shape"] = _fill_branch(placed, cols)
    if cols >= 6 and profile["n_block"] >= 1 and profile["n"] >= 4:
        scores["sidebar"] = _sidebar_branch(placed, cols, rows)
    scores["nested"] = _nested_branch(parsed, profile)
    if profile["n"] <= 3:
        scores["few_fill"] = _few_card_branch(placed, cols, rows)
    if cols >= 6 and profile["n"] >= 4:
        banners = sum(
            1
            for card in placed
            if int(card["w"]) == cols and not _is_first_header(card, placed)
        )
        scores["not_all_banners"] = 1.0 - banners / float(profile["n"])
    return scores


def page_structure_stats(
    placed: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> dict[str, float]:
    """按当前序列激活的结构分支计算整页拟合，各项范围 [0, 1]。

    structure_fit / row_band_rate：激活分支的均值，作为终局结构分。
    typed_band_rate：剖分子区域里按类型计的成行/成列分（诊断）。
    nested_split：能否剖成行/列树；横竖都有时更高。
    """
    n = len(placed)
    empty = {
        "row_band_rate": 0.0,
        "typed_band_rate": 0.0,
        "structure_fit": 0.0,
        "nested_split": 0.0,
        "row_coverage": 0.0,
        "split_reuse": 0.0,
        "type_split": 1.0,
        "thin_banner_rate": 0.0,
        "ones_rate": 0.0,
    }
    if n == 0:
        return empty
    parsed = _parse_slice(placed, (0, 0, cols, rows))
    by_id_credit: dict[int, float] = {}
    for axis, box, siblings in parsed["groups"]:
        for card in siblings:
            by_id_credit[id(card)] = _typed_credit_in_group(
                card, siblings, axis, box, cols
            )
    groups = _row_band_groups(placed)
    credits: list[float] = []
    for card in placed:
        if id(card) in by_id_credit:
            credits.append(by_id_credit[id(card)])
            continue
        credits.append(
            _typed_band_credit(
                card,
                groups[(int(card["y"]), int(card["h"]))],
                cols,
            )
        )
    typed = sum(credits) / float(n)
    nested = 0.5 * float(parsed["ok"]) + 0.5 * float(parsed["bidirectional"])
    covered = 0
    for (_y, height), band in groups.items():
        if _band_counts_as_coverage(band, cols):
            covered += int(height)
    thin = sum(
        1
        for card in placed
        if int(card["w"]) == cols
        and int(card["h"]) == 1
        and _card_type_name(card) not in HEADER_BAND_TYPES
    )
    ones = sum(1 for card in placed if int(card["w"]) * int(card["h"]) == 1)
    branches = _sequence_branch_scores(
        placed, cols, rows, parsed, parsed["groups"]
    )
    fit = sum(branches.values()) / float(len(branches))
    return {
        "row_band_rate": fit,
        "typed_band_rate": typed,
        "structure_fit": fit,
        "nested_split": nested,
        "row_coverage": min(covered, max(1, rows)) / float(max(1, rows)),
        "split_reuse": _split_reuse_score(groups, cols),
        "type_split": _same_type_split_score(placed, cols, parsed["groups"]),
        "thin_banner_rate": thin / float(n),
        "ones_rate": ones / float(n),
        **{f"branch_{name}": value for name, value in branches.items()},
    }


def page_structure_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """终局结构分：只激活当前序列里实际出现的类型分支。"""
    stats = page_structure_stats(
        list(ctx.get("placed") or []),
        max(1, int(ctx.get("cols") or 1)),
        max(1, int(ctx.get("rows") or 1)),
    )
    details = {
        "page_structure": 0.0,
        "row_band_rate": stats["row_band_rate"],
        "typed_band_rate": stats["typed_band_rate"],
        "structure_fit": stats["structure_fit"],
        "nested_split": stats["nested_split"],
        "row_coverage": stats["row_coverage"],
        "split_reuse": stats["split_reuse"],
        "type_split": stats["type_split"],
        "thin_banner_rate": stats["thin_banner_rate"],
        "ones_rate": stats["ones_rate"],
    }
    for key, value in stats.items():
        if key.startswith("branch_"):
            details[key] = value
    if not ctx.get("terminated") and not ctx.get("truncated"):
        return 0.0, details
    reward = PAGE_STRUCTURE_WEIGHT * float(stats["structure_fit"])
    details["page_structure"] = reward
    return reward, details


def area_share_errors(
    placed: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> list[float]:
    """每张已放卡相对整页面积份额的相对误差（与奖励同一公式）。"""
    if not queue:
        return []
    mins: list[int] = []
    for card in queue:
        wh = type_min_wh(str(card.get("type") or ""))
        mins.append(max(1, wh[0] * wh[1]) if wh else 1)
    seq = max(1, sum(mins))
    page = float(max(1, cols * rows))
    by_id = {
        str(card.get("id")): mins[i]
        for i, card in enumerate(queue)
        if card.get("id") is not None
    }
    errors: list[float] = []
    for i, card in enumerate(placed):
        min_area = by_id.get(str(card.get("id")))
        if min_area is None:
            typ = str(card.get("type") or "")
            wh = type_min_wh(typ)
            min_area = max(1, wh[0] * wh[1]) if wh else 1
        share = (min_area / float(seq)) * page
        placed_area = max(0, int(card["w"])) * max(0, int(card["h"]))
        gap = max(0.0, abs(placed_area - share) - AREA_SHARE_TOLERANCE_CELLS)
        errors.append(gap / max(share, 1.0))
    return errors


def layout_quality_metrics(
    placed: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> dict[str, float]:
    """评估用的页面质量：面积误差、成行率、空白率、1×1 数量。"""
    stats = page_structure_stats(placed, cols, rows)
    errors = area_share_errors(placed, queue, cols, rows)
    ones = sum(1 for card in placed if int(card["w"]) * int(card["h"]) == 1)
    filled = sum(max(0, int(card["w"])) * max(0, int(card["h"])) for card in placed)
    page = float(max(1, cols * rows))
    return {
        "area_share_error": (
            sum(errors) / float(len(errors)) if errors else 0.0
        ),
        "row_band_rate": stats["row_band_rate"],
        "split_reuse": stats["split_reuse"],
        "blank_rate": max(0.0, min(1.0, 1.0 - filled / page)),
        "ones_count": float(ones),
        "ones_rate": stats["ones_rate"],
    }


REWARD_TERMS: list[RewardFn] = [
    # 依赖专家标注，已关闭：
    # imitation_reward,  # 对齐专家 (w,h)
    # 内容尺寸约束：需要 HTTP layout-check；当前明确关闭。
    # layout_wh_reward,  # 暂时关闭接口奖励（layout-check HTTP）
    # 类型默认最小格来自固定样例，容易误判真实 Card，当前关闭。
    # packability_reward,
    # 开头 text 矮通栏；showcase/stat 连续同型时跳过。
    structure_reward,
    # min_size_reward,  # 面积下限改由 area_share 约束
    # 面积贴着份额。
    area_share_reward,
    # 邻卡逐步对齐已关闭，改终局整页结构。
    # row_align_reward,
    page_structure_reward,
    # 终局：空白率与未放完，不再给恒定 +100。
    terminal_reward,
]


def compute_reward(ctx: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """汇总本步所有分项。

    输入 ctx（env 已更新占用与放置后再调用）:
        valid / terminated / truncated / fail_reason
        card, x, y, w, h
        placed / remaining / cols / rows / cursor / total_cards
        occupancy / density

    输出:
        ``reward`` 是所有已启用奖励项的直接加和，没有额外归一化；
        ``details`` 保存每项原始分数并写入 ``info["reward_components"]``，
        可用于训练日志和逐项诊断。
    """
    total = 0.0
    details: dict[str, float] = {}
    for term in REWARD_TERMS:
        reward, part = term(ctx)
        total += float(reward)
        details.update(part)
    details["total"] = total
    return total, details
