"""为一次强化学习布局任务生成待放置卡片（不含 x/y）。

设计原则：
1. 参考经典网页/仪表盘骨架（Holy Grail、双栏博客、Dashboard Shell、卡片栅格等）
2. 先在网格上「搭好」不重叠布局，再导出卡片尺寸 —— 保证集合一定可摆下
3. 同一组重复卡保持同尺寸，贴合真实页面规律
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

COLOR_BY_ROLE = {
    "header": "#5eb887",
    "nav": "#4a9b7a",
    "hero": "#3d8bfd",
    "card": "#9b6bdf",
    "kpi": "#e6a23c",
    "list_item": "#6b8cae",
    "sidebar": "#d9776f",
    "panel": "#2aa8a0",
    "main": "#5b8def",
    "footer": "#c45c9a",
    "tile": "#e6a23c",
    "table": "#7a8b9a",
}

# 经典布局权重（名称对齐常见 UI 骨架）
PATTERN_WEIGHTS: dict[str, float] = {
    "holy_grail": 1.3,  # header / sidebar+main / footer
    "two_column_blog": 1.2,  # header / main+aside / footer
    "three_column": 1.0,  # header / left+main+right / footer
    "dashboard_shell": 1.5,  # rail + topbar + KPI 条 + chart/panel + table
    "card_gallery": 1.3,  # header + 等分卡片栅格 + footer
    "landing_hero": 1.2,  # header + hero + feature 卡行 + footer
    "magazine": 1.1,  # header + 大图文 + 侧边堆叠卡
    "feed_list": 1.1,  # header + 筛选 + 等宽列表行 + footer
    "app_shell": 1.2,  # 全高侧栏 + 顶栏 + 内容区卡片
}


@dataclass(frozen=True)
class PaletteItem:
    """与前端 PaletteItem 同形，并附带 RL 结构元数据。"""

    type: str
    label: str
    w: int
    h: int
    color: str
    role: str = "card"
    group_id: str = ""
    pattern: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlacedRect:
    """布局阶段的占位矩形（导出卡片时剥掉坐标）。"""

    x: int
    y: int
    w: int
    h: int
    role: str
    group_id: str
    label: str = ""


@dataclass
class _Board:
    cols: int
    rows: int
    rng: random.Random
    pattern: str
    placed: list[PlacedRect] = field(default_factory=list)

    def add(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        *,
        role: str,
        group_id: str,
        label: str = "",
    ) -> None:
        if w <= 0 or h <= 0:
            return
        if x < 0 or y < 0 or x + w > self.cols or y + h > self.rows:
            raise ValueError(
                f"out of bounds: ({x},{y},{w},{h}) on {self.cols}x{self.rows} [{self.pattern}]"
            )
        rect = PlacedRect(x, y, w, h, role, group_id, label)
        for other in self.placed:
            if _overlap(rect, other):
                raise ValueError(
                    f"overlap {role}@{x},{y} {w}x{h} with {other.role}@{other.x},{other.y}"
                )
        self.placed.append(rect)


def _overlap(a: PlacedRect, b: PlacedRect) -> bool:
    return not (
        a.x + a.w <= b.x
        or b.x + b.w <= a.x
        or a.y + a.h <= b.y
        or b.y + b.h <= a.y
    )


def _role_label(role: str) -> str:
    return {
        "header": "顶栏",
        "nav": "导航",
        "hero": "主视觉",
        "card": "卡片",
        "kpi": "指标",
        "list_item": "列表行",
        "sidebar": "侧栏",
        "panel": "面板",
        "main": "主内容",
        "footer": "底栏",
        "tile": "方块",
        "table": "表格",
    }.get(role, "卡片")


def _pick_div(n: int, choices: list[int]) -> int:
    """从候选中选能整除 n 的值；没有则选最接近的。"""
    exact = [c for c in choices if c >= 1 and c <= n and n % c == 0]
    if exact:
        return exact[0] if len(exact) == 1 else exact[len(exact) // 2]
    valid = [c for c in choices if 1 <= c <= n]
    return valid[-1] if valid else 1


# ---------------------------------------------------------------------------
# 经典布局：全部先占位，几何保证可摆
# 参考：MDN Common web layouts / CSS Grid Holy Grail /
#       Dashboard shell (sidebar + KPI strip + chart grid)
# ---------------------------------------------------------------------------


def _layout_holy_grail(b: _Board) -> None:
    """Holy Grail：顶栏 + 侧栏|主区 + 底栏。"""
    header_h, footer_h = 1, 1
    mid_h = b.rows - header_h - footer_h
    if mid_h < 2:
        header_h = footer_h = 0
        mid_h = b.rows

    y = 0
    if header_h:
        b.add(0, y, b.cols, header_h, role="header", group_id="header")
        y += header_h

    side_w = _pick_div(b.cols, [2, 3] if b.cols >= 8 else [1, 2])
    side_w = min(side_w, max(1, b.cols // 3))
    main_w = b.cols - side_w
    # 侧栏在左（经典）或右
    if b.rng.random() < 0.7:
        b.add(0, y, side_w, mid_h, role="sidebar", group_id="nav")
        b.add(side_w, y, main_w, mid_h, role="main", group_id="main")
    else:
        b.add(0, y, main_w, mid_h, role="main", group_id="main")
        b.add(main_w, y, side_w, mid_h, role="sidebar", group_id="aside")
    y += mid_h

    if footer_h:
        b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_two_column_blog(b: _Board) -> None:
    """双栏博客：顶栏 + 宽主栏 + 窄侧栏 + 底栏。"""
    header_h, footer_h = 1, 1
    mid_h = b.rows - header_h - footer_h
    if mid_h < 3:
        mid_h = b.rows
        header_h = footer_h = 0

    y = 0
    if header_h:
        b.add(0, y, b.cols, header_h, role="header", group_id="header")
        y += header_h

    aside_w = max(1, min(3, b.cols // 3))
    main_w = b.cols - aside_w
    # 主栏内再切：上文章区 + 下相关卡（同尺寸重复）
    article_h = max(2, (mid_h * 2) // 3)
    rest_h = mid_h - article_h
    b.add(0, y, main_w, article_h, role="main", group_id="article")

    if rest_h >= 1 and main_w >= 2:
        card_w = _pick_div(main_w, [2, 3, 4])
        n = main_w // card_w
        for i in range(n):
            b.add(
                i * card_w,
                y + article_h,
                card_w,
                rest_h,
                role="card",
                group_id="related",
            )
    elif rest_h >= 1:
        b.add(0, y + article_h, main_w, rest_h, role="panel", group_id="related")

    b.add(main_w, y, aside_w, mid_h, role="sidebar", group_id="widgets")
    y += mid_h
    if footer_h:
        b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_three_column(b: _Board) -> None:
    """三栏：顶栏 + 左导航|主内容|右 aside + 底栏。"""
    if b.cols < 6:
        _layout_holy_grail(b)
        return

    header_h, footer_h = 1, 1
    mid_h = b.rows - header_h - footer_h
    y = 0
    b.add(0, y, b.cols, header_h, role="header", group_id="header")
    y += header_h

    left_w = max(1, b.cols // 5)
    right_w = max(1, b.cols // 5)
    main_w = b.cols - left_w - right_w
    b.add(0, y, left_w, mid_h, role="nav", group_id="left_nav")
    b.add(left_w, y, main_w, mid_h, role="main", group_id="main")
    b.add(left_w + main_w, y, right_w, mid_h, role="sidebar", group_id="right_aside")
    y += mid_h
    b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_dashboard_shell(b: _Board) -> None:
    """Dashboard Shell：全高侧栏 + 顶栏 + KPI 条 + 图表面板 + 底表。"""
    rail_w = max(1, min(3, b.cols // 5))
    content_w = b.cols - rail_w
    if content_w < 3:
        rail_w = 1
        content_w = b.cols - 1

    b.add(0, 0, rail_w, b.rows, role="sidebar", group_id="rail")

    top_h = 1
    b.add(rail_w, 0, content_w, top_h, role="header", group_id="topbar")

    y = top_h
    # KPI：一行等分 3~4 张（能整除 content_w）
    kpi_n = 4 if content_w % 4 == 0 else (3 if content_w % 3 == 0 else 2)
    kpi_n = min(kpi_n, content_w)
    while content_w % kpi_n != 0 and kpi_n > 1:
        kpi_n -= 1
    kpi_w = content_w // kpi_n
    kpi_h = 1 if b.rows >= 8 else 1
    for i in range(kpi_n):
        b.add(rail_w + i * kpi_w, y, kpi_w, kpi_h, role="kpi", group_id="kpi")
    y += kpi_h

    # 图表区：约 2/3 宽主图 + 1/3 侧面板
    rest = b.rows - y
    if rest < 2:
        return
    table_h = 1 if rest >= 4 else 0
    mid_h = rest - table_h
    chart_w = max(2, (content_w * 2) // 3)
    side_w = content_w - chart_w
    b.add(rail_w, y, chart_w, mid_h, role="panel", group_id="chart", label=f"图表 {chart_w}×{mid_h}")
    if side_w > 0:
        b.add(
            rail_w + chart_w,
            y,
            side_w,
            mid_h,
            role="panel",
            group_id="detail",
            label=f"明细 {side_w}×{mid_h}",
        )
    y += mid_h
    if table_h:
        b.add(rail_w, y, content_w, table_h, role="table", group_id="table")


def _layout_card_gallery(b: _Board) -> None:
    """卡片画廊：顶栏 + 等分栅格（列宽整除）+ 底栏。"""
    header_h, footer_h = 1, 1
    body_h = b.rows - header_h - footer_h
    if body_h < 2:
        body_h = b.rows
        header_h = footer_h = 0

    y = 0
    if header_h:
        b.add(0, y, b.cols, header_h, role="header", group_id="header")
        y += header_h

    # 选能整除的列宽与行高，铺满 body（可不铺满最后一行缺口——通过选整除避免）
    col_choices = [c for c in (2, 3, 4, 5) if c <= b.cols and b.cols % c == 0]
    if not col_choices:
        col_choices = [1]
    card_w = b.rng.choice(col_choices)
    cols_n = b.cols // card_w

    row_h_choices = [h for h in (1, 2, 3) if h <= body_h and body_h % h == 0]
    if not row_h_choices:
        row_h_choices = [1]
    card_h = b.rng.choice(row_h_choices)
    rows_n = body_h // card_h

    for r in range(rows_n):
        for c in range(cols_n):
            b.add(
                c * card_w,
                y + r * card_h,
                card_w,
                card_h,
                role="card",
                group_id="gallery",
            )
    y += body_h
    if footer_h:
        b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_landing_hero(b: _Board) -> None:
    """落地页：顶栏 + Hero + 等分 feature 卡 + 底栏。"""
    header_h, footer_h = 1, 1
    y = 0
    b.add(0, y, b.cols, header_h, role="header", group_id="header")
    y += header_h

    avail = b.rows - header_h - footer_h
    hero_h = max(2, min(avail // 2, 3 if b.rows >= 8 else 2))
    feat_h = avail - hero_h
    if feat_h < 1:
        hero_h = avail
        feat_h = 0

    b.add(0, y, b.cols, hero_h, role="hero", group_id="hero")
    y += hero_h

    if feat_h >= 1:
        n = 3 if b.cols % 3 == 0 else (2 if b.cols % 2 == 0 else 1)
        cw = b.cols // n
        for i in range(n):
            b.add(i * cw, y, cw, feat_h, role="card", group_id="feature")
        y += feat_h

    b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_magazine(b: _Board) -> None:
    """杂志/媒体：顶栏 + 左侧大主卡 + 右侧堆叠同尺寸卡 + 底栏。"""
    header_h, footer_h = 1, 1
    mid_h = b.rows - header_h - footer_h
    y = 0
    b.add(0, y, b.cols, header_h, role="header", group_id="header")
    y += header_h

    feat_w = max(2, (b.cols * 2) // 3)
    side_w = b.cols - feat_w
    b.add(0, y, feat_w, mid_h, role="hero", group_id="featured")

    if side_w > 0:
        stack_n = 2 if mid_h >= 4 else 1
        while mid_h % stack_n != 0 and stack_n > 1:
            stack_n -= 1
        sh = mid_h // stack_n
        for i in range(stack_n):
            b.add(feat_w, y + i * sh, side_w, sh, role="card", group_id="stack")
    y += mid_h
    b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_feed_list(b: _Board) -> None:
    """信息流：顶栏 + 可选筛选条 + 等宽列表行 + 底栏。"""
    header_h, footer_h = 1, 1
    y = 0
    b.add(0, y, b.cols, header_h, role="header", group_id="header")
    y += header_h

    filter_h = 1 if b.rows >= 8 and b.rng.random() < 0.7 else 0
    if filter_h:
        b.add(0, y, b.cols, filter_h, role="panel", group_id="filter", label=f"筛选条 {b.cols}×1")
        y += filter_h

    body_h = b.rows - y - footer_h
    if body_h < 1:
        body_h = 1
        footer_h = 0

    # 每行等高铺满，保证可摆
    row_h = 1
    n = body_h // row_h
    for i in range(n):
        b.add(0, y + i * row_h, b.cols, row_h, role="list_item", group_id="feed_row")
    y += n * row_h
    if footer_h:
        b.add(0, y, b.cols, footer_h, role="footer", group_id="footer")


def _layout_app_shell(b: _Board) -> None:
    """应用壳：全高侧栏 + 内容区顶栏 + 内容卡片栅格。"""
    rail_w = max(1, min(2, b.cols // 4))
    content_w = b.cols - rail_w
    b.add(0, 0, rail_w, b.rows, role="sidebar", group_id="app_nav")

    top_h = 1
    b.add(rail_w, 0, content_w, top_h, role="header", group_id="topbar")

    body_h = b.rows - top_h
    y = top_h
    # 内容区等分卡片
    col_choices = [c for c in (2, 3, 4) if c <= content_w and content_w % c == 0] or [1]
    card_w = b.rng.choice(col_choices)
    cols_n = content_w // card_w
    row_h_choices = [h for h in (1, 2) if h <= body_h and body_h % h == 0] or [1]
    card_h = b.rng.choice(row_h_choices)
    rows_n = body_h // card_h
    for r in range(rows_n):
        for c in range(cols_n):
            b.add(
                rail_w + c * card_w,
                y + r * card_h,
                card_w,
                card_h,
                role="card",
                group_id="workspace",
            )


LAYOUT_BUILDERS: dict[str, Callable[[_Board], None]] = {
    "holy_grail": _layout_holy_grail,
    "two_column_blog": _layout_two_column_blog,
    "three_column": _layout_three_column,
    "dashboard_shell": _layout_dashboard_shell,
    "card_gallery": _layout_card_gallery,
    "landing_hero": _layout_landing_hero,
    "magazine": _layout_magazine,
    "feed_list": _layout_feed_list,
    "app_shell": _layout_app_shell,
}


# ---------------------------------------------------------------------------
# 可摆放校验（独立于生成：对导出卡片做 first-fit 验证）
# ---------------------------------------------------------------------------


def can_pack(cards: list[PaletteItem], cols: int, rows: int) -> bool:
    """判断卡片集合是否存在一种无重叠摆法（first-fit 扫描，偏保守）。"""
    # 大块优先，降低碎片
    ordered = sorted(cards, key=lambda c: (c.w * c.h, c.h, c.w), reverse=True)
    occupied = [[False] * cols for _ in range(rows)]

    def fits(x: int, y: int, w: int, h: int) -> bool:
        if x + w > cols or y + h > rows:
            return False
        for yy in range(y, y + h):
            row = occupied[yy]
            for xx in range(x, x + w):
                if row[xx]:
                    return False
        return True

    def fill(x: int, y: int, w: int, h: int) -> None:
        for yy in range(y, y + h):
            row = occupied[yy]
            for xx in range(x, x + w):
                row[xx] = True

    for card in ordered:
        placed = False
        for y in range(0, rows - card.h + 1):
            for x in range(0, cols - card.w + 1):
                if fits(x, y, card.w, card.h):
                    fill(x, y, card.w, card.h)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            return False
    return True


def _placed_to_cards(placed: list[PlacedRect], pattern: str) -> list[PaletteItem]:
    cards: list[PaletteItem] = []
    for i, p in enumerate(placed):
        cards.append(
            PaletteItem(
                type=f"rl_{p.role}_{i}",
                label=p.label or f"{_role_label(p.role)} {p.w}×{p.h}",
                w=p.w,
                h=p.h,
                color=COLOR_BY_ROLE.get(p.role, "#3d8bfd"),
                role=p.role,
                group_id=p.group_id,
                pattern=pattern,
            )
        )
    return cards


def list_patterns() -> list[str]:
    return list(LAYOUT_BUILDERS.keys())


def generate_episode_cards(
    *,
    cols: int = 10,
    rows: int = 10,
    min_count: Optional[int] = None,
    max_count: Optional[int] = None,
    max_area_ratio: float = 1.0,
    seed: Optional[int] = None,
    pattern: Optional[str] = None,
    ensure_packable: bool = True,
) -> list[PaletteItem]:
    """
    按经典页面骨架生成一次 RL 布局 episode 的卡片列表。

    - 先在 cols×rows 网格上构造不重叠占位，再导出尺寸（默认保证可摆下）
    - max_area_ratio < 1 时，从占位结果中按组裁掉部分重复卡，并再次校验可摆性
    - 不返回坐标 x/y（RL 任务自行布局）；需要参考解时可改用 generate_episode_layout
    """
    if pattern is not None and pattern not in LAYOUT_BUILDERS:
        raise ValueError(f"unknown pattern: {pattern}; choose from {list_patterns()}")

    rng = random.Random(seed)
    if pattern is None:
        names = list(PATTERN_WEIGHTS.keys())
        weights = [PATTERN_WEIGHTS[n] for n in names]
        pattern = rng.choices(names, weights=weights, k=1)[0]

    board = _Board(cols=cols, rows=rows, rng=rng, pattern=pattern)
    LAYOUT_BUILDERS[pattern](board)
    cards = _placed_to_cards(board.placed, pattern)

    # 面积裁剪：优先去掉重复组中的多余实例，保留骨架件（header/footer/sidebar/hero/main）
    area_budget = int(cols * rows * max_area_ratio)
    used = sum(c.w * c.h for c in cards)
    if used > area_budget:
        cards = _trim_to_area(cards, area_budget)

    if max_count is not None and len(cards) > max_count:
        cards = _trim_to_count(cards, max_count)

    if min_count is not None and len(cards) < min_count:
        # 经典布局本身件数可能很少（如 holy_grail 仅 4 块）；不强制灌水破坏可摆性
        pass

    if ensure_packable and not can_pack(cards, cols, rows):
        # 裁剪后若不可摆，回退到完整占位导出（一定可摆）
        cards = _placed_to_cards(board.placed, pattern)
        if max_count is not None and len(cards) > max_count:
            # 保骨架裁剪到 max_count，并校验
            trimmed = _trim_to_count(cards, max_count)
            cards = trimmed if can_pack(trimmed, cols, rows) else cards[:max_count]
            if not can_pack(cards, cols, rows):
                cards = _placed_to_cards(board.placed, pattern)

    return cards


def generate_episode_layout(
    *,
    cols: int = 10,
    rows: int = 10,
    seed: Optional[int] = None,
    pattern: Optional[str] = None,
) -> list[PlacedRect]:
    """生成带坐标的参考布局（调试/演示用）。"""
    if pattern is not None and pattern not in LAYOUT_BUILDERS:
        raise ValueError(f"unknown pattern: {pattern}; choose from {list_patterns()}")
    rng = random.Random(seed)
    if pattern is None:
        names = list(PATTERN_WEIGHTS.keys())
        weights = [PATTERN_WEIGHTS[n] for n in names]
        pattern = rng.choices(names, weights=weights, k=1)[0]
    board = _Board(cols=cols, rows=rows, rng=rng, pattern=pattern)
    LAYOUT_BUILDERS[pattern](board)
    return list(board.placed)


_SKELETON_ROLES = frozenset({"header", "footer", "sidebar", "nav", "hero", "main", "table"})


def _trim_to_area(cards: list[PaletteItem], budget: int) -> list[PaletteItem]:
    used = sum(c.w * c.h for c in cards)
    if used <= budget:
        return cards
    # 从重复组（非骨架）末尾删除
    result = list(cards)
    removable_idx = [
        i
        for i, c in enumerate(result)
        if c.role not in _SKELETON_ROLES and c.group_id not in {"header", "footer", "rail", "app_nav"}
    ]
    while used > budget and removable_idx:
        i = removable_idx.pop()
        used -= result[i].w * result[i].h
        result.pop(i)
        removable_idx = [j if j < i else j - 1 for j in removable_idx]
    return result


def _trim_to_count(cards: list[PaletteItem], max_count: int) -> list[PaletteItem]:
    if len(cards) <= max_count:
        return cards
    skeleton = [c for c in cards if c.role in _SKELETON_ROLES]
    others = [c for c in cards if c.role not in _SKELETON_ROLES]
    keep_others = max(0, max_count - len(skeleton))
    return skeleton + others[:keep_others]


if __name__ == "__main__":
    for name in list_patterns():
        cards = generate_episode_cards(seed=42, pattern=name, cols=10, rows=10)
        ok = can_pack(cards, 10, 10)
        area = sum(c.w * c.h for c in cards)
        print(f"\n=== {name}  n={len(cards)} area={area}/100 packable={ok} ===")
        for card in cards:
            print(
                f"  {card.role:10} {card.w}×{card.h}  group={card.group_id or '-':16} {card.label}"
            )
