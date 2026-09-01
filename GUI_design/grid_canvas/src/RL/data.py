"""读取 data/ 下的布局 episode（jsonl）。

每条 episode 含 grid、cards_wh、target_xy 等字段，供 LayoutEnv 采样与评估。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR, design_jsonl, sample_jsonl


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


def load_episodes(source: str = "design") -> list[dict[str, Any]]:
    """加载指定数据源的全部 episode。

    输入:
        source: 数据源别名或自定义 jsonl 路径。
            - "design" -> design_mockups.jsonl
            - "sample" / "dataset" / "both" -> sample_layouts.jsonl
            - 其它字符串 -> 当作文件路径
    输出:
        episode 字典列表；空文件时 ValueError。
    逻辑:
        根据 source 解析路径，iter_jsonl 读入内存列表。
    """
    if source == "design":
        path = design_jsonl()
    elif source in {"sample", "dataset", "both"}:
        path = sample_jsonl()
    else:
        path = Path(source)
    episodes = list(iter_jsonl(path))
    if not episodes:
        raise ValueError(f"empty dataset: {path}")
    return episodes


def get_episode(episode_id: str, source: str = "sample") -> dict[str, Any]:
    """按 id 查找单个 episode。

    输入:
        episode_id: episode["id"]。
        source: 优先搜索的数据源（默认 sample）。
    输出:
        匹配的 episode dict。
    逻辑:
        先在 source 中查找；未命中再扫 design；仍无则 KeyError。
    """
    for ep in load_episodes(source):
        if ep["id"] == episode_id:
            return ep
    for ep in load_episodes("design"):
        if ep["id"] == episode_id:
            return ep
    raise KeyError(f"episode not found: {episode_id}")
