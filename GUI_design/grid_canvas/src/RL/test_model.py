"""加载已训练 MaskablePPO，在数据集上评估并导出布局序列。

用法:
  cd GUI_design/grid_canvas/src
  python -m RL.test_model
  python -m RL.test_model Model/20260809_185345/layout_maskable_ppo
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from . import config as cfg
    from .data import load_episodes
    from .env import LayoutEnv
else:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL import config as cfg
    from RL.data import load_episodes
    from RL.env import LayoutEnv


def latest_checkpoint(model_root: Path | None = None) -> Path:
    """查找最新训练权重路径。

    输入:
        model_root: Model/ 根目录；默认 cfg.MODEL_SAVE_PATH。
    输出:
        checkpoint 路径（无 .zip 后缀）。
    逻辑:
        优先 Model/<时间戳>/layout_maskable_ppo；否则回退 Model/layout_maskable_ppo。
    """
    root = model_root or cfg.MODEL_SAVE_PATH
    stamped = sorted(
        (p for p in root.glob("*") if p.is_dir() and (p / f"{cfg.CHECKPOINT_NAME}.zip").exists()),
        key=lambda p: p.name,
        reverse=True,
    )
    if stamped:
        return stamped[0] / cfg.CHECKPOINT_NAME

    legacy = root / cfg.CHECKPOINT_NAME
    if legacy.with_suffix(".zip").exists() or legacy.exists():
        return legacy
    raise FileNotFoundError(f"未找到模型，请先训练。目录: {root}")


def resolve_model_path(arg: str | None = None) -> Path:
    """解析 CLI 传入的模型路径。

    输入:
        arg: None=latest_checkpoint；相对/绝对路径均可。
    输出:
        存在的 checkpoint Path。
    """
    if not arg:
        return latest_checkpoint()
    path = Path(arg)
    if not path.is_absolute():
        candidates = [
            path,
            cfg.PKG_ROOT / path,
            cfg.PKG_ROOT / "Model" / path,
        ]
        for cand in candidates:
            if cand.with_suffix(".zip").exists() or cand.exists():
                return cand
        raise FileNotFoundError(f"找不到模型: {arg}")
    return path


def load_model(model_path: Path):
    """从磁盘加载 MaskablePPO 权重。

    输入:
        model_path: SB3 save 路径（可带或不带 .zip）。
    输出:
        MaskablePPO 实例。
    """
    from sb3_contrib import MaskablePPO

    return MaskablePPO.load(str(model_path))


def run_episode(
    model,
    env: LayoutEnv,
    *,
    episode: dict[str, Any] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """对单条 episode 做确定性 rollout。

    输入:
        model: 已加载策略。
        env: LayoutEnv 实例（可复用）。
        episode: 指定 layout；None 则 env 自行采样。
        seed: 传给 env.reset。
    输出:
        结果 dict: episode_id, success, fail_reason, sequence, placed, reward 等。
    """
    options = {"episode": episode} if episode is not None else None
    obs, info0 = env.reset(seed=seed, options=options)
    done = False
    total_reward = 0.0
    info = info0
    while not done:
        masks = env.action_masks()
        action, _ = model.predict(obs, action_masks=masks, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(int(action))
        total_reward += float(reward)
        done = terminated or truncated

    placed = info.get("placed") or list(env._placed)
    return {
        "episode_id": info.get("episode_id") or info0.get("episode_id"),
        "success": bool(info.get("success")),
        "fail_reason": info.get("fail_reason"),
        "n_cards": info0.get("n_cards"),
        "placed_n": len(placed),
        "cols": info0.get("cols"),
        "rows": info0.get("rows"),
        "reward": round(total_reward, 4),
        "sequence": info.get("sequence") or env.get_layout_sequence(),
        "placed": placed,
    }


def test_model(
    model_path: Path | None = None,
    *,
    source: str | None = None,
    use_all_episodes: bool = True,
    episodes: int | None = None,
    save_json: bool = True,
) -> dict[str, Any]:
    """批量评估并可选写入 test_results.json。

    输入:
        model_path: 权重路径；None=最新。
        source: 数据集别名。
        use_all_episodes: True=跑全量 dataset；False=随机 n 局。
        episodes: use_all_episodes=False 时的局数。
        save_json: 是否写入模型目录下 test_results.json。
    输出:
        summary dict: success, total, rate, results[]。
    """
    path = model_path or latest_checkpoint()
    source = source or cfg.SOURCE
    print(f"model  -> {path}")
    print(f"source -> {source!r}")

    model = load_model(path)
    env = LayoutEnv(source=source)

    results: list[dict[str, Any]] = []
    if use_all_episodes:
        dataset = load_episodes(source)
        print(f"episodes -> {len(dataset)} (full dataset)")
        for i, ep in enumerate(dataset):
            results.append(run_episode(model, env, episode=ep, seed=cfg.SEED + i))
    else:
        n = episodes or cfg.EVAL_EPISODES
        print(f"episodes -> {n} (random sample)")
        for i in range(n):
            results.append(run_episode(model, env, seed=cfg.SEED + i))

    ok = sum(1 for r in results if r["success"])
    total = len(results)
    summary = {
        "model": str(path),
        "source": source,
        "success": ok,
        "total": total,
        "rate": ok / max(1, total),
        "results": results,
    }

    print("-" * 60)
    for r in results:
        ep_id = r["episode_id"]
        if r["success"]:
            print(f"  ok  [{ep_id}] reward={r['reward']:.2f}")
            print(f"       {r['sequence']}")
        else:
            print(
                f"  fail[{ep_id}] reason={r['fail_reason']} "
                f"placed={r['placed_n']}/{r['n_cards']} reward={r['reward']:.2f}"
            )
            if r["sequence"]:
                print(f"       partial={r['sequence']}")
    print("-" * 60)
    print(f"eval success {ok}/{total} ({summary['rate']:.0%})")

    if save_json:
        out_dir = path.parent if path.parent != cfg.MODEL_SAVE_PATH else cfg.MODEL_SAVE_PATH
        out_path = out_dir / "test_results.json"
        out_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"saved  -> {out_path}")

    return summary


def main() -> None:
    """CLI 入口：python -m RL.test_model [model_path]。"""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        model_path = resolve_model_path(arg)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    test_model(model_path)


if __name__ == "__main__":
    main()
