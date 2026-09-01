"""MaskablePPO 训练入口。

流程: 建环境 → 并行 rollout → learn → 存权重 → 训练集/额外集评估。

用法:
  cd GUI_design/grid_canvas/src
  python -m RL.train
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from . import config as cfg
    from .env import LayoutEnv
else:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL import config as cfg
    from RL.env import LayoutEnv


def make_env():
    """返回 DummyVecEnv 所需的环境工厂（thunk）。

    输出:
        无参 callable，每次调用创建 Monitor(ActionMasker(LayoutEnv))。
    逻辑:
        ActionMasker 在 predict 时过滤非法 (x,y,w,h)；
        Monitor 记录 ep_rew_mean 等训练日志指标。
    """

    def _thunk():
        from sb3_contrib.common.wrappers import ActionMasker
        from stable_baselines3.common.monitor import Monitor

        def mask_fn(env):
            base = env.unwrapped if hasattr(env, "unwrapped") else env
            return base.action_masks()

        env = Monitor(LayoutEnv(source=cfg.SOURCE))
        return ActionMasker(env, mask_fn)

    return _thunk


def build_model(venv):
    """构建 MaskablePPO 模型（MultiInput 策略，适配 Dict 观测）。

    输入:
        venv: DummyVecEnv 包装的并行环境。
    输出:
        未训练的 MaskablePPO 实例；超参来自 config.py。
    """
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.policies import MaskableMultiInputActorCriticPolicy

    return MaskablePPO(
        MaskableMultiInputActorCriticPolicy,
        venv,
        verbose=1,
        learning_rate=cfg.LEARNING_RATE,
        n_steps=cfg.N_STEPS,
        batch_size=cfg.BATCH_SIZE,
        gamma=cfg.GAMMA,
        ent_coef=cfg.ENT_COEF,
        tensorboard_log=cfg.TENSORBOARD_LOG or None,
        seed=cfg.SEED,
    )


def _load_eval_episodes(source: str):
    """解析评估用 episode 列表。

    输入:
        source: 同 data.load_episodes；"classic" 为 sample 中非 design- 子集。
    输出:
        episode dict 列表。
    """
    if __package__:
        from .data import load_episodes
    else:
        from RL.data import load_episodes

    if source == "classic":
        return [
            ep
            for ep in load_episodes("sample")
            if not str(ep.get("id", "")).startswith("design-")
        ]
    return load_episodes(source)


def evaluate(
    model,
    *,
    source: str | None = None,
    episodes: int | None = None,
    label: str | None = None,
) -> float:
    """确定性 rollout 评估成功率。

    输入:
        model: 已训练 MaskablePPO。
        source: 数据集别名；默认 cfg.SOURCE。
        episodes: 限制评估条数；None=全量。
        label: 日志前缀。
    输出:
        成功率 float，范围 [0,1]。
    逻辑:
        对每个 episode reset(options={"episode": ep})，greedy 选合法动作直至结束；
        success=全部卡放完且无 fail_reason。
    """
    source = source or cfg.SOURCE
    dataset = _load_eval_episodes(source)
    if episodes is not None:
        dataset = dataset[: max(1, episodes)]

    tag = label or source
    env = LayoutEnv(source="design" if source == "classic" else source)
    ok = 0
    print(f"[eval:{tag}] episodes -> {len(dataset)}")
    for i, ep in enumerate(dataset):
        obs, info0 = env.reset(seed=cfg.SEED + i, options={"episode": ep})
        done = False
        info = info0
        while not done:
            masks = env.action_masks()
            action, _ = model.predict(obs, action_masks=masks, deterministic=True)
            obs, _r, term, trunc, info = env.step(int(action))
            done = term or trunc
        success = bool(info.get("success"))
        ok += int(success)
        ep_id = info.get("episode_id")
        if success and info.get("sequence"):
            print(f"  ok  [{ep_id}] {info['sequence']}")
        else:
            placed = info.get("placed") or []
            print(
                f"  fail[{ep_id}] reason={info.get('fail_reason')} "
                f"placed={len(placed)}/{info0.get('n_cards')}"
            )
    rate = ok / max(1, len(dataset))
    print(f"[eval:{tag}] success {ok}/{len(dataset)} ({rate:.0%})")
    return rate


def evaluate_after_train(model) -> None:
    """训练结束后依次评估 SOURCE 与 EVAL_EXTRA_SOURCES。"""
    print("=" * 60)
    print(f"post-train eval: train-set source={cfg.SOURCE!r}")
    evaluate(model, source=cfg.SOURCE, label=f"train/{cfg.SOURCE}")

    extras = getattr(cfg, "EVAL_EXTRA_SOURCES", ()) or ()
    for extra in extras:
        print("=" * 60)
        print(f"post-train eval: extra source={extra!r}")
        evaluate(model, source=extra, label=f"extra/{extra}")
    print("=" * 60)


def train() -> None:
    """完整训练管线：VecEnv → learn → save → evaluate_after_train。"""
    try:
        from stable_baselines3.common.vec_env import DummyVecEnv
    except ImportError as exc:
        raise SystemExit(
            "缺少依赖，请先: pip install -r RL/requirements.txt\n"
            f"原始错误: {exc}"
        ) from exc

    run_dir = cfg.new_run_dir()
    print(
        f"source={cfg.SOURCE!r} timesteps={cfg.TIMESTEPS} "
        f"n_envs={cfg.N_ENVS} lr={cfg.LEARNING_RATE}"
    )
    print(f"run_dir -> {run_dir}")
    print(f"post-eval extras -> {getattr(cfg, 'EVAL_EXTRA_SOURCES', ())}")
    factory = make_env()
    venv = DummyVecEnv([factory for _ in range(cfg.N_ENVS)])
    model = build_model(venv)
    model.learn(total_timesteps=cfg.TIMESTEPS, progress_bar=True)

    out = cfg.checkpoint_path(run_dir)
    model.save(str(out))
    print(f"saved model -> {out}.zip")
    evaluate_after_train(model)


def main() -> None:
    train()


if __name__ == "__main__":
    main()
