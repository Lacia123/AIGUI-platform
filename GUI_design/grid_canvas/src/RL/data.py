"""读取并校验 clean schema v3 布局 episode（jsonl）。

输入为 grid + card_queue（无几何）；expert_cards 仅供训练奖励/评估。
"""

from __future__ import annotations

import json
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

from .config import (
    MAX_CARDS,
    MAX_CARD_H,
    MAX_CARD_W,
    MAX_COLS,
    MAX_ROWS,
    TEST_DATA_DIR,
    design_jsonl,
    handcrafted_jsonl,
    psuip_jsonl,
    sample_jsonl,
    synth_jsonl,
    test_data_jsonls,
)


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """逐行读取 jsonl，跳过空行。

    输入:
        path: jsonl 文件路径。
    输出:
        每行解析后的 dict 迭代器。
    逻辑:
        文件不存在时抛出 FileNotFoundError 并提示先导出数据集。
    """
    if not path.exists():
        raise FileNotFoundError(
            f"缺少数据文件: {path}\n请先运行: python -m RL.tools.export_sample_dataset"
        )
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def validate_episode(ep: dict[str, Any]) -> None:
    """拒绝错误 schema、超上限画布和不可达专家框，避免静默截断。"""
    ep_id = str(ep.get("id", "<unknown>"))
    if int(ep.get("schema_version", 0)) != 3:
        raise ValueError(f"episode {ep_id}: 需要 schema_version=3")
    queue = ep.get("card_queue")
    experts = ep.get("expert_cards", [])
    if not isinstance(queue, list) or not queue:
        raise ValueError(f"episode {ep_id}: card_queue 必须是非空列表")
    if not isinstance(experts, list):
        raise ValueError(f"episode {ep_id}: expert_cards 必须是列表")
    if len(queue) > MAX_CARDS:
        raise ValueError(f"episode {ep_id}: cards={len(queue)} > MAX_CARDS={MAX_CARDS}")
    grid = ep.get("grid") or {}
    cols, rows = int(grid.get("cols", 0)), int(grid.get("rows", 0))
    if not (1 <= cols <= MAX_COLS and 1 <= rows <= MAX_ROWS):
        raise ValueError(
            f"episode {ep_id}: grid={cols}x{rows} 超出上限 {MAX_COLS}x{MAX_ROWS}"
        )
    queue_ids = [str(c.get("id", "")) for c in queue]
    if not all(queue_ids) or len(set(queue_ids)) != len(queue_ids):
        raise ValueError(f"episode {ep_id}: card_queue id 为空或重复")
    expert_ids: set[str] = set()
    for box in experts:
        cid = str(box.get("id", ""))
        if cid not in queue_ids or cid in expert_ids:
            raise ValueError(f"episode {ep_id}: expert id={cid!r} 缺失于队列或重复")
        expert_ids.add(cid)
        x, y = int(box["x"]), int(box["y"])
        w, h = int(box["w"]), int(box["h"])
        if not (1 <= w <= MAX_CARD_W and 1 <= h <= MAX_CARD_H):
            raise ValueError(
                f"episode {ep_id}/{cid}: size={w}x{h} 超出 {MAX_CARD_W}x{MAX_CARD_H}"
            )
        if x < 0 or y < 0 or x + w > cols or y + h > rows:
            raise ValueError(f"episode {ep_id}/{cid}: expert 框越界")


def load_episodes(source: str = "all") -> list[dict[str, Any]]:
    """加载指定数据源的全部 episode。

    输入:
        source: 数据源别名或自定义 jsonl 路径。
            - "all" -> sample_layouts.jsonl + handcrafted_layouts.jsonl
            - "handcrafted" -> handcrafted_layouts.jsonl
            - "testdata" / "test" -> data/test_data/*.jsonl
            - "psuip" -> psuip_typed_layouts.jsonl
            - "design" -> design_mockups.jsonl
            - "sample" / "dataset" -> sample_layouts.jsonl
            - "synth" -> synth_layouts.jsonl
            - 其它字符串 -> 当作文件路径
    输出:
        episode 字典列表；空文件时 ValueError。
    逻辑:
        根据 source 解析路径，iter_jsonl 读入内存列表。
    """
    if source == "all":
        paths = [sample_jsonl(), handcrafted_jsonl()]
    elif source == "psuip":
        path = psuip_jsonl()
        paths = [path]
    elif source == "design":
        path = design_jsonl()
        paths = [path]
    elif source in {"sample", "dataset"}:
        path = sample_jsonl()
        paths = [path]
    elif source == "handcrafted":
        path = handcrafted_jsonl()
        paths = [path]
    elif source == "synth":
        path = synth_jsonl()
        paths = [path]
    elif source in {"test", "testdata"}:
        paths = test_data_jsonls()
        if not paths:
            raise ValueError(f"empty testdata dir: {TEST_DATA_DIR}")
    else:
        path = Path(source)
        paths = [path]
    episodes = [ep for item in paths for ep in iter_jsonl(item)]
    if not episodes:
        raise ValueError(f"empty dataset: {', '.join(map(str, paths))}")
    for ep in episodes:
        validate_episode(ep)
    return episodes


def episode_grid_size(ep: dict[str, Any]) -> tuple[int, int]:
    """返回 episode 的 (cols, rows)。"""
    grid = ep.get("grid") or {}
    return int(grid.get("cols") or 0), int(grid.get("rows") or 0)


def filter_episodes_by_grid(
    episodes: list[dict[str, Any]],
    cols: int,
    rows: int,
) -> list[dict[str, Any]]:
    """只保留指定网格的 episode。"""
    return [ep for ep in episodes if episode_grid_size(ep) == (int(cols), int(rows))]


def load_training_episodes(source: str | None = None) -> list[dict[str, Any]]:
    """加载训练用 episode。SOURCE 命中且设置了 TRAIN_GRID 时只留该网格。"""
    from . import config as cfg

    source = source or cfg.SOURCE
    episodes = load_episodes(source)
    grid = getattr(cfg, "TRAIN_GRID", None)
    if grid is None or source != cfg.SOURCE:
        return episodes
    cols, rows = int(grid[0]), int(grid[1])
    kept = filter_episodes_by_grid(episodes, cols, rows)
    if not kept:
        raise ValueError(f"TRAIN_GRID={cols}x{rows} 在 source={source!r} 中没有页面")
    return kept


def get_episode(episode_id: str, source: str = "sample") -> dict[str, Any]:
    """按 id 查找单个 episode。

    输入:
        episode_id: episode["id"]。
        source: 优先搜索的数据源（默认 sample）。
    输出:
        匹配的 episode dict。
    逻辑:
        先在 source 中查找；未命中再扫 psuip / design；仍无则 KeyError。
    """
    for ep in load_episodes(source):
        if ep["id"] == episode_id:
            return ep
    for fallback in ("psuip", "design"):
        if fallback == source:
            continue
        for ep in load_episodes(fallback):
            if ep["id"] == episode_id:
                return ep
    raise KeyError(f"episode not found: {episode_id}")


def _content_signature(card: dict[str, Any]) -> tuple[Any, ...]:
    """可部署内容签名：长度分桶 + 结构布尔，不含专家几何。"""
    from .layout import psuip_content_features

    feats = psuip_content_features(str(card.get("psuip") or ""))
    # 长度分 8 桶，避免极小字符差制造伪冲突
    len_bucket = int(feats["psuip_len_n"] * 8)
    return (
        len_bucket,
        int(feats["has_table"] > 0.5),
        int(feats["has_list"] > 0.5),
        int(feats["has_image"] > 0.5),
    )


def observation_signature(ep: dict[str, Any]) -> tuple[Any, ...]:
    """观测别名签名：grid + 有序类型序列 + 内容特征。

    相同签名意味着策略在开局看到的可部署输入无法区分这两局。
    """
    grid = ep.get("grid") or {}
    cols, rows = int(grid.get("cols") or 0), int(grid.get("rows") or 0)
    queue = list(ep.get("card_queue") or [])
    types = tuple(str(c.get("type") or "") for c in queue)
    contents = tuple(_content_signature(c) for c in queue)
    return (cols, rows, types, contents)


def expert_action_signature(ep: dict[str, Any]) -> tuple[Any, ...]:
    """专家动作序列签名：(id, x, y, w, h) 按 card_queue 顺序。"""
    experts = {str(b["id"]): b for b in (ep.get("expert_cards") or [])}
    parts: list[tuple[Any, ...]] = []
    for card in ep.get("card_queue") or []:
        cid = str(card.get("id") or "")
        box = experts.get(cid) or {}
        parts.append(
            (
                cid,
                int(box.get("x") or -1),
                int(box.get("y") or -1),
                int(box.get("w") or -1),
                int(box.get("h") or -1),
            )
        )
    return tuple(parts)


def audit_observation_aliasing(
    episodes: list[dict[str, Any]] | None = None,
    *,
    source: str = "all",
    warn: bool = True,
) -> dict[str, Any]:
    """审计「相同可观测输入 → 不同专家动作」的冲突组。

    返回:
        total_episodes / conflict_groups / conflict_episodes / groups
        groups 每项含 signature、episode_ids、expert_variants。
    """
    episodes = list(episodes if episodes is not None else load_episodes(source))
    by_sig: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for ep in episodes:
        by_sig[observation_signature(ep)].append(ep)

    groups: list[dict[str, Any]] = []
    conflict_ids: list[str] = []
    for sig, eps in by_sig.items():
        expert_vars = {expert_action_signature(ep) for ep in eps}
        if len(expert_vars) <= 1:
            continue
        ids = [str(ep.get("id") or "?") for ep in eps]
        conflict_ids.extend(ids)
        groups.append(
            {
                "grid": (sig[0], sig[1]),
                "types": sig[2],
                "episode_ids": ids,
                "expert_variants": len(expert_vars),
            }
        )

    report = {
        "total_episodes": len(episodes),
        "unique_obs_signatures": len(by_sig),
        "conflict_groups": len(groups),
        "conflict_episodes": len(set(conflict_ids)),
        "groups": groups,
    }
    if warn and groups:
        warnings.warn(
            f"观测别名冲突: {len(groups)} 组 / {len(set(conflict_ids))} 条 episode "
            f"共享可观测输入却有不同专家动作。内容不同的应靠内容特征区分；"
            f"内容也相同的属于多模态目标。",
            stacklevel=2,
        )
        preview = ", ".join(
            f"{g['episode_ids']}@{g['grid']}" for g in groups[:5]
        )
        print(
            f"[data:audit] observation alias conflicts={len(groups)} "
            f"episodes={len(set(conflict_ids))} preview={preview}",
            flush=True,
        )
    elif warn:
        print(
            f"[data:audit] observation alias conflicts=0 "
            f"(episodes={len(episodes)}, signatures={len(by_sig)})",
            flush=True,
        )
    return report


def split_episodes_by_grid(
    episodes: list[dict[str, Any]],
    *,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按 (cols, rows) 分层切分 train/val，尽量保留同类型异布局样本。"""
    import numpy as np

    rng = np.random.default_rng(seed)
    by_grid: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for ep in episodes:
        grid = ep.get("grid") or {}
        key = (int(grid.get("cols") or 0), int(grid.get("rows") or 0))
        by_grid[key].append(ep)

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    for _size, bucket in sorted(by_grid.items()):
        order = list(bucket)
        rng.shuffle(order)
        if len(order) == 1:
            train.extend(order)
            continue
        n_val = max(1, int(round(len(order) * val_ratio)))
        n_val = min(n_val, len(order) - 1)
        val.extend(order[:n_val])
        train.extend(order[n_val:])
    return train, val


def has_same_type_varied_layout(ep: dict[str, Any]) -> bool:
    """同页内同类型专家尺寸不全相同 → 异布局样本。"""
    experts = {str(b["id"]): b for b in (ep.get("expert_cards") or [])}
    by_type: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for card in ep.get("card_queue") or []:
        cid = str(card.get("id") or "")
        box = experts.get(cid)
        if not box:
            continue
        typ = str(card.get("type") or "")
        by_type[typ].add((int(box["w"]), int(box["h"])))
    return any(len(sizes) > 1 for sizes in by_type.values())
