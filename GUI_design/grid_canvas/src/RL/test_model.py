"""加载已训练 MaskablePPO，对 PSUIP 类型队列预测完整布局。

主路径与训练一致：输入只有画布、类型队列和当前棋盘，无尺寸提示/专家框。
  cd GUI_design/grid_canvas/src
  python -m RL.test_model --psuip path/to/file.psuip.md --preset desktop
  python -m RL.test_model Model/20260903_181120 --psuip path/to/file.psuip.md --preset phone
  # 不传路径时用 config.TEST_MODEL / TEST_CKPT；TEST_MODEL 为空则取最新目录

可选：在数据集上回归评估，并按类型样例渲染完整 PSUIP 文件
  python -m RL.test_model --eval
  python -m RL.test_model --eval --split val --ckpt best
  python -m RL.test_model --eval --source all
  python -m RL.test_model --eval --source psuip --psuip-out Model/out/psuip_renders
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__:
    from . import config as cfg
    from .card_types import (
        CARD_OBS_DIM,
        LAYOUT_STATS_DIM,
        OBS_SCHEMA_VERSION,
        SPATIAL_CHANNELS,
    )
    from .data import load_episodes, split_episodes_by_grid
    from .env import LayoutEnv
    from .policy import LayoutFeaturesExtractor
    from .psuip_content import extract_snippets
    from .search import policy_beam_search
    from .train import run_episode
else:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL import config as cfg
    from RL.card_types import (
        CARD_OBS_DIM,
        LAYOUT_STATS_DIM,
        OBS_SCHEMA_VERSION,
        SPATIAL_CHANNELS,
    )
    from RL.data import load_episodes, split_episodes_by_grid
    from RL.env import LayoutEnv
    from RL.policy import LayoutFeaturesExtractor
    from RL.psuip_content import extract_snippets
    from RL.search import policy_beam_search
    from RL.train import run_episode

# 与 tools/export_sample_dataset.PRESETS / 训练数据对齐（格数）
PRESET_GRID: dict[str, tuple[int, int]] = {
    "phone": (1, 3),
    "tablet": (3, 4),
    "desktop": (5, 3),
    "dashboard": (7, 3),
    "square": (3, 3),
}

# 页面像素（写入 layout:grid width/height）
PRESET_PAGE_PX: dict[str, tuple[int, int]] = {
    "phone": (390, 844),
    "tablet": (768, 1024),
    "desktop": (1280, 800),
    "dashboard": (1880, 680),
    "square": (800, 800),
}

_CARD_SAMPLES_CACHE: dict[str, str] | None = None


def load_card_type_samples() -> dict[str, str]:
    """读取 card_type_samples.json：type → 裸 PSUIP 占位文本。"""
    global _CARD_SAMPLES_CACHE
    if _CARD_SAMPLES_CACHE is not None:
        return _CARD_SAMPLES_CACHE
    path = cfg.DATA_DIR / "card_type_samples.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples = raw.get("samples") or {}
    _CARD_SAMPLES_CACHE = {
        str(k): str(v.get("psuip") or "").strip()
        for k, v in samples.items()
        if isinstance(v, dict) and v.get("psuip")
    }
    return _CARD_SAMPLES_CACHE


def resolve_page_px(
    *,
    preset: str | None = None,
    grid: dict[str, Any] | None = None,
    width: int | None = None,
    height: int | None = None,
) -> tuple[int, int]:
    """解析 layout:grid 的像素宽高。显式 width/height > grid 字段 > preset > desktop。"""
    if width is not None and height is not None:
        return int(width), int(height)
    grid = grid or {}
    gw, gh = grid.get("width"), grid.get("height")
    if gw is not None and gh is not None:
        return int(gw), int(gh)
    name = preset or grid.get("preset_id") or "desktop"
    if name in PRESET_PAGE_PX:
        return PRESET_PAGE_PX[name]
    return PRESET_PAGE_PX["desktop"]


def _indent_block(text: str, prefix: str = "  ") -> str:
    lines = text.splitlines() or [""]
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in lines)


def _safe_filename(name: str) -> str:
    text = str(name or "episode").strip() or "episode"
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text)


def card_sample_body(type_name: str | None, samples: dict[str, str] | None = None) -> str:
    """按类型取占位文本；缺失时写注释占位。"""
    samples = samples or load_card_type_samples()
    key = str(type_name or "")
    body = (samples.get(key) or "").strip()
    if body:
        return body
    return f"<!-- missing card sample for type={key or 'unknown'!r} -->"


def render_placed_psuip(
    placed: list[dict[str, Any]],
    *,
    cols: int,
    rows: int,
    gap: int = 16,
    samples: dict[str, str] | None = None,
) -> str:
    """把模型放置结果渲染成完整可渲染 PSUIP。

    - 外层：`<layout:grid width="{cols}" gap="{gap}" height="{rows}">`（网格列/行数，非像素）
    - 每张已放卡：`<grid:item x y width height>`（坐标由 RL 0-index 转为 PSUIP 1-index）
    - 卡内正文：按 type 从 card_type_samples.json 取占位文本
    """
    samples = samples or load_card_type_samples()
    blocks: list[str] = []
    for p in placed:
        if p.get("x") is None or p.get("y") is None:
            continue
        # example2 / 渲染器使用 1-index 格坐标
        x = int(p["x"]) + 1
        y = int(p["y"]) + 1
        w = int(p["w"])
        h = int(p["h"])
        body = card_sample_body(p.get("type"), samples)
        blocks.append(
            f'<grid:item x="{x}" y="{y}" width="{w}" height="{h}">\n'
            f"{_indent_block(body)}\n"
            f"</grid:item>"
        )
    inner = "\n\n".join(blocks)
    if inner:
        inner = f"\n{inner}\n"
    return (
        f'<layout:grid width="{int(cols)}" gap="{int(gap)}" '
        f'height="{int(rows)}">{inner}</layout:grid>\n'
    )


def save_rendered_psuip(
    text: str,
    out_dir: Path,
    episode_id: str,
) -> Path:
    """每个 episode 写一个 .psuip.md 文件。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_safe_filename(episode_id)}.psuip.md"
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return path


def _zip_stem(path: Path) -> Path:
    """SB3 保存/加载都不带 .zip 后缀。"""
    return path.with_suffix("") if path.suffix == ".zip" else path


def _checkpoint_in_dir(run_dir: Path, ckpt: str = "auto") -> Path | None:
    """在一次训练目录里选权重：auto 优先 best，否则 final。"""
    final_name = cfg.CHECKPOINT_NAME
    best_name = getattr(cfg, "BEST_CHECKPOINT_NAME", "layout_maskable_ppo_best")
    best = run_dir / best_name
    final = run_dir / final_name
    has_best = best.with_suffix(".zip").is_file() or best.is_file()
    has_final = final.with_suffix(".zip").is_file() or final.is_file()
    if ckpt == "best":
        return best if has_best else None
    if ckpt == "final":
        return final if has_final else None
    if has_best:
        return best
    if has_final:
        return final
    return None


def latest_checkpoint(model_root: Path | None = None, *, ckpt: str = "auto") -> Path:
    """查找最新训练权重路径（Model/<时间戳>/layout_maskable_ppo[_best]）。"""
    root = model_root or cfg.MODEL_SAVE_PATH
    stamped = sorted(
        (p for p in root.glob("*") if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for run_dir in stamped:
        found = _checkpoint_in_dir(run_dir, ckpt=ckpt)
        if found is not None:
            return found

    legacy = _checkpoint_in_dir(root, ckpt=ckpt)
    if legacy is not None:
        return legacy
    raise FileNotFoundError(f"未找到模型，请先训练。目录: {root}")


def _default_test_model() -> str | None:
    """config.TEST_MODEL：空字符串视为未指定，回落到最新目录。"""
    raw = str(getattr(cfg, "TEST_MODEL", "") or "").strip()
    return raw or None


def _default_test_ckpt() -> str:
    """config.TEST_CKPT，非法值回落到 auto。"""
    raw = str(getattr(cfg, "TEST_CKPT", "auto") or "auto").strip().lower()
    return raw if raw in ("auto", "best", "final") else "auto"


def resolve_model_path(arg: str | None = None, *, ckpt: str = "auto") -> Path:
    """解析模型路径；None/空=config.TEST_MODEL，仍空则最新 checkpoint。

    可传:
      - Model/20260916_185957/layout_maskable_ppo
      - Model/20260916_185957/（目录，auto 优先 *_best）
      - 绝对/相对 .zip
    """
    text = str(arg).strip() if arg else ""
    if not text:
        text = _default_test_model() or ""
    if not text:
        return latest_checkpoint(ckpt=ckpt)
    path = Path(text)
    if not path.is_absolute():
        search_roots = [path, cfg.PKG_ROOT / path, cfg.PKG_ROOT / "Model" / path]
    else:
        search_roots = [path]

    for cand in search_roots:
        if cand.with_suffix(".zip").is_file() or cand.is_file():
            return _zip_stem(cand)
        if cand.is_dir():
            nested = _checkpoint_in_dir(cand, ckpt=ckpt)
            if nested is not None:
                return nested
    raise FileNotFoundError(f"找不到模型: {arg}")


def _check_model_meta(meta: dict[str, Any]) -> None:
    """核对 checkpoint 与当前观测/网络契约。"""
    expected = {
        "obs_schema_version": OBS_SCHEMA_VERSION,
        "card_obs_dim": CARD_OBS_DIM,
        "spatial_channels": SPATIAL_CHANNELS,
        "layout_stats_dim": LAYOUT_STATS_DIM,
        "action_mode": "top_left_anchor_wh",
        "action_space_size": cfg.action_space_size(),
        "features_dim": int(getattr(cfg, "FEATURES_DIM", 256)),
        "card_d_model": int(getattr(cfg, "CARD_D_MODEL", 128)),
        "card_n_layers": int(getattr(cfg, "CARD_N_LAYERS", 3)),
        "fuse_res_blocks": int(getattr(cfg, "FUSE_RES_BLOCKS", 2)),
    }
    mismatches: list[str] = []
    for key, want in expected.items():
        if key not in meta:
            mismatches.append(f"{key}=缺失(需要 {want})")
            continue
        got = meta[key]
        try:
            got_n = int(got)
        except (TypeError, ValueError):
            got_n = got
        if got_n != want:
            mismatches.append(f"{key}={got} (当前 {want})")
    if mismatches:
        raise RuntimeError(
            "checkpoint 与当前训练环境不匹配: "
            + ", ".join(mismatches)
            + "。请重新训练: python -m RL.train"
        )


def load_model(model_path: Path):
    """从磁盘加载 MaskablePPO；必要时校验 model_meta 并挂上 VecNormalize 统计。

    当前观测为 spatial 5ch / cards(N,18) / grid 5 维；融合为 5-token + ResMLP。
    旧 checkpoint 不兼容。奖励归一化不影响 predict（norm_obs=False）。
    """
    from sb3_contrib import MaskablePPO

    run_dir = Path(model_path).parent
    meta_path = run_dir / "model_meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"无法读取 {meta_path}: {exc}") from exc
        _check_model_meta(meta)
        print(
            f"meta   -> schema=v{meta.get('obs_schema_version')} "
            f"card_dim={meta.get('card_obs_dim')} "
            f"d_model={meta.get('card_d_model')} "
            f"layers={meta.get('card_n_layers')} "
            f"fuse_res={meta.get('fuse_res_blocks')}"
        )
    else:
        print(f"warn   -> 无 {meta_path.name}，跳过契约校验")

    # 先 import 特征提取器，供 SB3 unpickle 解析类
    _ = LayoutFeaturesExtractor
    try:
        model = MaskablePPO.load(str(model_path))
    except Exception as exc:
        raise RuntimeError(
            f"加载模型失败: {model_path}\n"
            "若报 observation / features_extractor 尺寸不匹配，说明 checkpoint 是旧网络。"
            "当前 State/融合层已升级，请重新训练: python -m RL.train"
        ) from exc

    vec_path = run_dir / "vecnormalize.pkl"
    if vec_path.is_file():
        print(f"vecnorm-> {vec_path}  (norm_obs=False，推理用原始观测)")
    else:
        print("vecnorm-> 未找到 vecnormalize.pkl")
    print(f"ckpt   -> {model_path}")
    return model


def resolve_grid(
    *,
    preset: str | None = None,
    cols: int | None = None,
    rows: int | None = None,
) -> tuple[str, int, int]:
    """解析画布尺寸；显式 cols/rows 优先，否则用 preset。"""
    if cols is not None and rows is not None:
        name = preset or f"custom-{cols}x{rows}"
        return name, int(cols), int(rows)
    name = preset or "desktop"
    if name not in PRESET_GRID:
        known = ", ".join(sorted(PRESET_GRID))
        raise ValueError(f"未知 preset={name!r}；可选: {known}")
    c, r = PRESET_GRID[name]
    return name, c, r


def episode_from_psuip(
    psuip_text: str,
    *,
    preset: str | None = "desktop",
    cols: int | None = None,
    rows: int | None = None,
    episode_id: str = "infer",
) -> dict[str, Any]:
    """把一段 PSUIP 切成卡片队列，构造成 LayoutEnv 可用的 episode。

    不提供任何几何尺寸或专家框；模型预测 (w,h)，位置由左上空白锚点确定。
    """
    text = (psuip_text or "").strip()
    if not text:
        raise ValueError("PSUIP 文本为空")

    snippets = extract_snippets(text)
    if not snippets:
        raise ValueError("未解析到任何卡片（检查标签或正文长度）")
    if len(snippets) > cfg.MAX_CARDS:
        snippets = snippets[: cfg.MAX_CARDS]

    preset_name, grid_cols, grid_rows = resolve_grid(
        preset=preset, cols=cols, rows=rows
    )

    card_queue: list[dict[str, Any]] = []
    for i, snip in enumerate(snippets):
        card: dict[str, Any] = {
            "id": f"c{i}",
            "type": snip["type"],
            "psuip": snip["psuip"],
        }
        card_queue.append(card)

    return {
        "schema_version": 3,
        "id": episode_id,
        "preset_id": preset_name,
        "grid": {"cols": grid_cols, "rows": grid_rows},
        "card_queue": card_queue,
        "expert_cards": [],
        "n_cards": len(card_queue),
    }


def _infer_episode(model, env: LayoutEnv, episode: dict[str, Any] | None, seed: int, beam: int):
    """推理一步：beam>1 走策略引导搜索，否则贪心。"""
    if beam > 1 and episode is not None:
        return policy_beam_search(
            model,
            env,
            episode,
            beam_width=beam,
            top_k=int(getattr(cfg, "INFER_POLICY_TOP_K", 4)),
        )
    return run_episode(model, env, episode=episode, seed=seed)


def layout_psuip(
    psuip_text: str,
    *,
    model_path: Path | None = None,
    preset: str | None = "desktop",
    cols: int | None = None,
    rows: int | None = None,
    seed: int | None = None,
    model=None,
    beam: int | None = None,
) -> dict[str, Any]:
    """推理入口：PSUIP 文本 → 每张卡的 type / x / y / w / h。

    输出:
        success, fail_reason, grid, cards[{id,type,x,y,w,h}], sequence, rendered_psuip
    """
    path = model_path or latest_checkpoint()
    ep = episode_from_psuip(
        psuip_text,
        preset=preset,
        cols=cols,
        rows=rows,
    )
    policy = model if model is not None else load_model(path)
    # source 仅用于构造 env；实际用 options.episode 覆盖
    env = LayoutEnv(source=cfg.SOURCE)
    beam_w = int(beam if beam is not None else getattr(cfg, "INFER_BEAM_WIDTH", 1))
    result = _infer_episode(
        policy,
        env,
        ep,
        seed if seed is not None else cfg.SEED,
        beam_w,
    )

    queue = env._queue
    cards_out: list[dict[str, Any]] = []
    placed_by_id = {str(p["id"]): p for p in result["placed"]}
    for card in queue:
        cid = str(card["id"])
        p = placed_by_id.get(cid)
        item: dict[str, Any] = {
            "id": cid,
            "type": card.get("type"),
        }
        if p is not None:
            item.update(
                {
                    "x": int(p["x"]),
                    "y": int(p["y"]),
                    "w": int(p["w"]),
                    "h": int(p["h"]),
                }
            )
        else:
            item.update({"x": None, "y": None, "w": None, "h": None})
        cards_out.append(item)

    page_w, page_h = resolve_page_px(preset=ep.get("preset_id"), grid=ep.get("grid"))
    cols = int(result["cols"] or (ep.get("grid") or {}).get("cols") or 0)
    rows = int(result["rows"] or (ep.get("grid") or {}).get("rows") or 0)
    rendered = render_placed_psuip(
        result["placed"],
        cols=cols,
        rows=rows,
    )

    return {
        "model": str(path),
        "preset": ep["preset_id"],
        "grid": {
            "cols": cols,
            "rows": rows,
            "width": page_w,
            "height": page_h,
        },
        "success": result["success"],
        "fail_reason": result["fail_reason"],
        "n_cards": result["n_cards"],
        "placed_n": result["placed_n"],
        "sequence": result["sequence"],
        "cards": cards_out,
        "rendered_psuip": rendered,
    }


def read_psuip_arg(psuip: str) -> str:
    """psuip 参数：已有文件路径则读文件，否则当作原文。"""
    path = Path(psuip)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    # 相对 RL 包 / 源稿目录再试一次
    for cand in (
        cfg.PKG_ROOT / psuip,
        cfg.psuip_source_dir() / psuip,
        Path.cwd() / psuip,
    ):
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    return psuip


def _select_eval_dataset(source: str, split: str) -> list[dict[str, Any]]:
    """按训练时同一套分层规则切 train/val。"""
    dataset = load_episodes(source)
    if split == "all":
        return dataset
    train_eps, val_eps = split_episodes_by_grid(
        dataset,
        val_ratio=float(getattr(cfg, "VAL_RATIO", 0.15)),
        seed=cfg.SEED,
    )
    if split == "train":
        return train_eps
    if split == "val":
        return val_eps
    raise ValueError(f"未知 split={split!r}；可选: all / train / val")


def test_model(
    model_path: Path | None = None,
    *,
    source: str | None = None,
    split: str = "all",
    use_all_episodes: bool = True,
    episodes: int | None = None,
    save_json: bool = True,
    save_psuip: bool = True,
    psuip_dir: Path | str | None = None,
    ckpt: str = "auto",
    beam: int | None = None,
) -> dict[str, Any]:
    """批量评估数据集（回归用）。

    另可将每条结果渲染为完整 PSUIP（layout:grid + grid:item + 类型占位文本），
    每个 episode 保存一个 `.psuip.md`。
    """
    path = model_path or latest_checkpoint(ckpt=ckpt)
    source = source or str(getattr(cfg, "TEST_SOURCE", None) or cfg.SOURCE)
    split = split or str(getattr(cfg, "TEST_SPLIT", "all") or "all")
    print(f"model  -> {path}")
    print(f"source -> {source!r}  split={split}")

    model = load_model(path)
    env = LayoutEnv(source=source)
    samples = load_card_type_samples()
    beam_w = int(beam if beam is not None else getattr(cfg, "INFER_BEAM_WIDTH", 1))
    print(f"beam   -> {beam_w}")

    out_dir = path.parent if path.parent != cfg.MODEL_SAVE_PATH else cfg.MODEL_SAVE_PATH
    render_dir = Path(psuip_dir) if psuip_dir else out_dir / "psuip_renders"

    results: list[dict[str, Any]] = []
    saved_psuip: list[str] = []
    if use_all_episodes:
        dataset = _select_eval_dataset(source, split)
        print(f"episodes -> {len(dataset)} ({split})")
        for i, ep in enumerate(dataset):
            result = _infer_episode(model, env, ep, cfg.SEED + i, beam_w)
            cols = int(result.get("cols") or (ep.get("grid") or {}).get("cols") or 0)
            rows = int(result.get("rows") or (ep.get("grid") or {}).get("rows") or 0)
            rendered = render_placed_psuip(
                result.get("placed") or [],
                cols=cols,
                rows=rows,
                samples=samples,
            )
            result["rendered_psuip"] = rendered
            result["grid_size"] = {"cols": cols, "rows": rows}
            results.append(result)
            if save_psuip:
                written = save_rendered_psuip(
                    rendered,
                    render_dir,
                    str(result.get("episode_id") or ep.get("id") or f"ep{i}"),
                )
                saved_psuip.append(str(written))
    else:
        n = episodes or max(1, cfg.EVAL_EPISODES)
        print(f"episodes -> {n} (random sample)")
        for i in range(n):
            result = _infer_episode(model, env, None, cfg.SEED + i, 1)
            cols = int(result.get("cols") or 0)
            rows = int(result.get("rows") or 0)
            rendered = render_placed_psuip(
                result.get("placed") or [],
                cols=cols,
                rows=rows,
                samples=samples,
            )
            result["rendered_psuip"] = rendered
            result["grid_size"] = {"cols": cols, "rows": rows}
            results.append(result)
            if save_psuip:
                written = save_rendered_psuip(
                    rendered,
                    render_dir,
                    str(result.get("episode_id") or f"random-{i}"),
                )
                saved_psuip.append(str(written))

    ok = sum(1 for r in results if r["success"])
    total = len(results)
    mean_iou = sum(float(r.get("mean_iou") or 0.0) for r in results) / max(1, total)
    mean_hit = sum(float(r.get("exact_hit_rate") or 0.0) for r in results) / max(
        1, total
    )
    mean_area = sum(float(r.get("area_share_error") or 0.0) for r in results) / max(1, total)
    mean_row = sum(float(r.get("row_band_rate") or 0.0) for r in results) / max(1, total)
    mean_blank = sum(float(r.get("blank_rate") or 0.0) for r in results) / max(1, total)
    mean_ones = sum(float(r.get("ones_count") or 0.0) for r in results) / max(1, total)
    exact_eps = sum(1 for r in results if r.get("exact_episode"))
    no_legal = sum(1 for r in results if r.get("fail_reason") == "no_legal_moves")

    # 固定回归：易堵死页 + handcrafted 模板前缀
    hard_fail_ids = {
        "tablet-gallery",
        "design-tablet-class-over",
        "design-tablet-exam-prep",
    }
    handcrafted_ids = {"1", "2", "3", "5", "7", "1-1"}
    hard_fails = [
        r for r in results if str(r.get("episode_id")) in hard_fail_ids and not r["success"]
    ]
    hc = [r for r in results if str(r.get("episode_id")) in handcrafted_ids]
    prefixes = []
    for r in hc:
        seq = str(r.get("sequence") or "")
        # 去掉 grid: 头，取前两张卡
        body = seq.split(";", 1)[-1]
        parts = body.split(")(")
        prefixes.append(")(".join(parts[:2]) if parts else body)

    shared_prefix_rate = 0.0
    if len(prefixes) >= 2:
        most = Counter(prefixes).most_common(1)[0][1]
        shared_prefix_rate = most / len(prefixes)

    # textCard 首步按 grid 分组
    first_text_by_grid: dict[str, list[str]] = {}
    for r in results:
        placed = r.get("placed") or []
        if not placed:
            continue
        first = placed[0]
        if str(first.get("type")) != "textCard":
            continue
        gkey = f"{r.get('cols')}x{r.get('rows')}"
        act = f"{first.get('w')}x{first.get('h')}@({first.get('x')},{first.get('y')})"
        first_text_by_grid.setdefault(gkey, []).append(act)

    by_grid: dict[str, dict[str, float]] = defaultdict(
        lambda: {"n": 0, "ok": 0, "iou": 0.0, "hit": 0.0}
    )
    for r in results:
        gkey = f"{r.get('cols')}x{r.get('rows')}"
        by_grid[gkey]["n"] += 1
        by_grid[gkey]["ok"] += int(bool(r.get("success")))
        by_grid[gkey]["iou"] += float(r.get("mean_iou") or 0.0)
        by_grid[gkey]["hit"] += float(r.get("exact_hit_rate") or 0.0)

    summary = {
        "model": str(path),
        "source": source,
        "split": split,
        "success": ok,
        "total": total,
        "rate": ok / max(1, total),
        "mean_iou": mean_iou,
        "exact_hit_rate": mean_hit,
        "mean_area_share_error": mean_area,
        "mean_row_band_rate": mean_row,
        "mean_blank_rate": mean_blank,
        "mean_ones_count": mean_ones,
        "exact_episode_rate": exact_eps / max(1, total),
        "no_legal_rate": no_legal / max(1, total),
        "hard_fail_ids": [r.get("episode_id") for r in hard_fails],
        "handcrafted_shared_prefix_rate": shared_prefix_rate,
        "textCard_first_by_grid": {
            k: dict(Counter(v)) for k, v in first_text_by_grid.items()
        },
        "by_grid": {
            k: {
                "n": int(v["n"]),
                "success_rate": v["ok"] / max(1, v["n"]),
                "mean_iou": v["iou"] / max(1, v["n"]),
                "exact_hit_rate": v["hit"] / max(1, v["n"]),
            }
            for k, v in by_grid.items()
        },
        "psuip_dir": str(render_dir) if save_psuip else None,
        "psuip_files": saved_psuip,
        "results": results,
    }

    print("-" * 60)
    for r in results:
        ep_id = r["episode_id"]
        iou = float(r.get("mean_iou") or 0.0)
        hit = float(r.get("exact_hit_rate") or 0.0)
        if r["success"]:
            print(
                f"  ok  [{ep_id}] reward={r['reward']:.2f} "
                f"area={float(r.get('area_share_error') or 0):.2f} "
                f"row={float(r.get('row_band_rate') or 0):.0%} "
                f"blank={float(r.get('blank_rate') or 0):.0%} "
                f"ones={float(r.get('ones_count') or 0):.0f}"
            )
        else:
            print(
                f"  fail[{ep_id}] reason={r['fail_reason']} "
                f"placed={r['placed_n']}/{r['n_cards']} reward={r['reward']:.2f} "
                f"area={float(r.get('area_share_error') or 0):.2f} "
                f"row={float(r.get('row_band_rate') or 0):.0%}"
            )
        if r.get("sequence"):
            print(f"       {r['sequence']}")
    print("-" * 60)
    print(
        f"eval success {ok}/{total} ({summary['rate']:.0%}) "
        f"area_err={mean_area:.3f} row_band={mean_row:.0%} "
        f"blank={mean_blank:.0%} ones={mean_ones:.2f} "
        f"no_legal={no_legal}"
    )
    for gkey, stats in sorted(by_grid.items()):
        gn = max(1, int(stats["n"]))
        print(
            f"  grid[{gkey}] n={gn} success={stats['ok']/gn:.0%} "
            f"iou={stats['iou']/gn:.3f} hit={stats['hit']/gn:.0%}"
        )
    for gkey, acts in sorted(first_text_by_grid.items()):
        top = Counter(acts).most_common(3)
        print(f"  textCard@first[{gkey}] " + ", ".join(f"{a}×{c}" for a, c in top))

    if save_json:
        out_path = out_dir / "test_results.json"
        # results 里含整段 PSUIP，完整写入便于回溯
        out_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"saved  -> {out_path}")
        # 纯文本：每行一条可直接粘贴的序列（无 JSON 转义）
        seq_path = out_dir / "test_sequences.txt"
        lines: list[str] = []
        for r in results:
            seq = (r.get("sequence") or "").strip()
            if not seq:
                continue
            lines.append(f"# {r.get('episode_id')} success={r.get('success')}")
            lines.append(seq)
            lines.append("")
        seq_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"saved  -> {seq_path}  (直接复制序列行即可渲染)")

    if save_psuip:
        print(f"saved  -> {render_dir}  ({len(saved_psuip)} psuip files)")

    return summary


def _print_layout_result(result: dict[str, Any]) -> None:
    g = result["grid"]
    print(f"model  -> {result['model']}")
    print(f"preset -> {result['preset']}  grid={g['cols']}x{g['rows']}")
    status = "ok" if result["success"] else f"fail:{result.get('fail_reason')}"
    print(f"status -> {status}  placed={result['placed_n']}/{result['n_cards']}")
    print("-" * 60)
    for c in result["cards"]:
        if c.get("x") is None:
            print(f"  [{c['id']}] type={c.get('type')}  (未放置)")
        else:
            print(
                f"  [{c['id']}] type={c.get('type')}  "
                f"x={c['x']} y={c['y']} w={c['w']} h={c['h']}"
            )
    print("-" * 60)
    # 整段可直接粘贴到页面「模型输出序列」→「渲染到大画布」
    seq = result.get("sequence") or ""
    print("【可渲染序列 — 复制下面一行到页面大画布】")
    print(seq)
    print("-" * 60)
    rendered = result.get("rendered_psuip") or ""
    if rendered:
        print("【完整 PSUIP（layout:grid + 类型占位）】")
        print(rendered.rstrip())
        print("-" * 60)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="PSUIP 布局推理 / 数据集评估",
    )
    parser.add_argument(
        "model",
        nargs="?",
        default=_default_test_model(),
        help=(
            "权重路径（默认 config.TEST_MODEL；"
            "该值为空则取最新 Model/<时间戳>/）"
        ),
    )
    parser.add_argument(
        "--psuip",
        type=str,
        default=None,
        help="PSUIP 文件路径，或直接传入 PSUIP 文本",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="desktop",
        choices=sorted(PRESET_GRID.keys()),
        help="画布预设（默认 desktop=5x3）",
    )
    parser.add_argument("--cols", type=int, default=None, help="覆盖画布列数")
    parser.add_argument("--rows", type=int, default=None, help="覆盖画布行数")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="将推理 JSON 写到该路径",
    )
    parser.add_argument(
        "--psuip-out",
        type=str,
        default=None,
        help="完整 PSUIP 输出目录（默认 Model/<run>/psuip_renders）",
    )
    parser.add_argument(
        "--no-psuip-render",
        action="store_true",
        help="不渲染/保存完整 PSUIP 文件",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="在数据集上评估（旧行为），而不是 PSUIP 推理",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(getattr(cfg, "TEST_SOURCE", None) or cfg.SOURCE),
        help="评估数据源（默认 config.TEST_SOURCE；testdata=data/test_data/*.jsonl）",
    )
    parser.add_argument(
        "--split",
        type=str,
        default=str(getattr(cfg, "TEST_SPLIT", "all") or "all"),
        choices=("all", "train", "val"),
        help="评估切分（默认 config.TEST_SPLIT）；val 与训练 held-out 规则一致",
    )
    parser.add_argument(
        "--ckpt",
        type=str,
        default=_default_test_ckpt(),
        choices=("auto", "best", "final"),
        help="选权重（默认 config.TEST_CKPT）：auto 优先 *_best，否则 final",
    )
    parser.add_argument(
        "--beam",
        type=int,
        default=None,
        help="策略引导 Beam 宽度；默认 config.INFER_BEAM_WIDTH，1=贪心",
    )
    args = parser.parse_args(argv)

    try:
        model_path = resolve_model_path(args.model, ckpt=args.ckpt)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    if args.eval or not args.psuip:
        if not args.psuip and not args.eval:
            # 无 --psuip 时保持兼容：跑数据集评估
            print("未指定 --psuip，执行数据集评估（可用 --psuip 做推理）")
        test_model(
            model_path,
            source=args.source,
            split=args.split,
            save_psuip=not args.no_psuip_render,
            psuip_dir=args.psuip_out,
            ckpt=args.ckpt,
            beam=args.beam,
        )
        return

    text = read_psuip_arg(args.psuip)
    try:
        result = layout_psuip(
            text,
            model_path=model_path,
            preset=args.preset,
            cols=args.cols,
            rows=args.rows,
            beam=args.beam,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    _print_layout_result(result)

    if not args.no_psuip_render:
        out_dir = (
            Path(args.psuip_out)
            if args.psuip_out
            else model_path.parent / "psuip_renders"
        )
        written = save_rendered_psuip(
            result.get("rendered_psuip") or "",
            out_dir,
            Path(args.psuip).stem if Path(args.psuip).suffix else "infer",
        )
        print(f"saved  -> {written}")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"saved  -> {out_path}")
    else:
        # 便于管道：最后输出可渲染整段（含 grid 头）
        print(result.get("sequence") or "")


if __name__ == "__main__":
    main()