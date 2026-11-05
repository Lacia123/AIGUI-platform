"""MaskablePPO 训练入口。

流程: 建环境 → 并行 rollout → learn → 存权重 → 训练集/额外集评估。

用法:
  cd GUI_design/grid_canvas/src
  python -m RL.train
  python RL/train.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__:
    from . import config as cfg
    from .card_types import (
        CARD_OBS_DIM,
        LAYOUT_STATS_DIM,
        OBS_SCHEMA_VERSION,
        SPATIAL_CHANNELS,
        TYPE_NAMES,
    )
    from .data import (
        audit_observation_aliasing,
        load_episodes,
        load_training_episodes,
        split_episodes_by_grid,
    )
    from .env import LayoutEnv
    from .policy import LayoutFeaturesExtractor
    from .reward import (
        annotation_exact_hit,
        annotation_l1_error,
        annotation_wh_iou_score,
        annotation_wh_error,
        annotation_xy_error,
        layout_quality_metrics,
    )
    from .search import (
        behavior_clone,
        collect_teacher_transitions,
    )
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
        TYPE_NAMES,
    )
    from RL.data import (
        audit_observation_aliasing,
        load_episodes,
        load_training_episodes,
        split_episodes_by_grid,
    )
    from RL.env import LayoutEnv
    from RL.policy import LayoutFeaturesExtractor
    from RL.reward import (
        annotation_exact_hit,
        annotation_l1_error,
        annotation_wh_iou_score,
        annotation_wh_error,
        annotation_xy_error,
        layout_quality_metrics,
    )
    from RL.search import (
        behavior_clone,
        collect_teacher_transitions,
    )


# 汇总打印时展示的奖励分项（与 reward.compute_reward details 对齐）
_REWARD_KEYS = (
    "imitation",
    "packability",
    "packability_area",
    "structure",
    "min_size",
    "area_share",
    "page_structure",
    "row_align",
    "align_edge",
    "align_split",
    "align_flush",
    "layout_wh",
    "logic",
    "logic_type_size",
    "logic_origin",
    "logic_adjacent",
    "terminal",
    "total",
)
# 比率/诊断字段按步覆盖，不按 episode 累加
_LAST_ONLY_KEYS = frozenset(
    {
        "blank_ratio",
        "expert_blank_ratio",
        "blank_error",
        "leftover_ratio",
        "fill_ratio",
        "layout_wh_valid",
        "layout_wh_reachable",
        "packability_ok",
        "structure_band",
        "structure_width_n",
        "area_share_target",
        "area_share_ratio",
        "area_share_ok",
        "row_band_rate",
        "typed_band_rate",
        "structure_fit",
        "nested_split",
        "row_coverage",
        "branch_tile",
        "branch_no_thin",
        "branch_header",
        "branch_stat_cluster",
        "branch_mist_cluster",
        "branch_block_shape",
        "branch_fill_shape",
        "branch_sidebar",
        "branch_nested",
        "branch_few_fill",
        "branch_not_all_banners",
        "split_reuse",
        "type_split",
        "thin_banner_rate",
        "ones_rate",
        "row_align_ok",
        "annotation_xy",
        "annotation_wh",
        "annotation_l1",
        "annotation_iou",
        "annotation_error",
        "annotation_distance_shaped",
        "annotation_shaped",
        "annotation_hit",
        "annotation_miss",
    }
)


def make_env(
    episodes: list[dict[str, Any]] | None = None,
    source: str | None = None,
):
    """返回 DummyVecEnv 所需的环境工厂（thunk）。

    输入:
        episodes: 可选训练子集；传入后环境不会重新加载完整 SOURCE。
        source: 覆盖 cfg.SOURCE；在线训练传 ``random``。
    输出:
        无参 callable，每次调用创建 Monitor(ActionMasker(LayoutEnv))。
    逻辑:
        ActionMasker 在 predict 时过滤左上锚点处非法的 (w,h)；
        Monitor 记录 ep_rew_mean 等训练日志指标。
    """
    source = source or cfg.SOURCE

    def _thunk():
        from sb3_contrib.common.wrappers import ActionMasker
        from stable_baselines3.common.monitor import Monitor

        def mask_fn(env):
            # DummyVecEnv / Monitor 会包一层，掩码仍要从 LayoutEnv 取
            base = env.unwrapped if hasattr(env, "unwrapped") else env
            return base.action_masks()

        # Monitor 在内层记 ep_rew；ActionMasker 在外层给 PPO 非法 (w,h) 掩码
        env = Monitor(LayoutEnv(source=source, episodes=episodes))
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
        n_epochs=cfg.N_EPOCHS,
        gamma=cfg.GAMMA,
        gae_lambda=cfg.GAE_LAMBDA,
        clip_range=cfg.CLIP_RANGE,
        ent_coef=cfg.ENT_COEF,
        vf_coef=cfg.VF_COEF,
        max_grad_norm=cfg.MAX_GRAD_NORM,
        target_kl=cfg.TARGET_KL,
        tensorboard_log=cfg.TENSORBOARD_LOG or None,
        seed=cfg.SEED,
        policy_kwargs={
            "features_extractor_class": LayoutFeaturesExtractor,
            "features_extractor_kwargs": {"features_dim": cfg.FEATURES_DIM},
            **(
                {"net_arch": cfg.NET_ARCH}
                if getattr(cfg, "NET_ARCH", None) is not None
                else {}
            ),
        },
    )


class TrainDetailCallback:
    """训练中汇总 episode 与 PPO 更新指标并打印 / 写入 train_detail.log。

    每个并行环境各自累加本局 reward_components；Monitor 在局结束时
    往 info 写入 ``episode``，此时把该局收进滑动窗口。窗口满
    ``every_episodes`` 局打一行 ``[train:ep]`` / ``[train:reward]``。
    每次 PPO rollout 结束再打 ``[train:update]``（loss / KL 等）。
    """

    @staticmethod
    def create(
        *,
        every_episodes: int = 20,
        every_updates: int = 1,
        log_path: Path | None = None,
    ):
        from stable_baselines3.common.callbacks import BaseCallback

        class _Callback(BaseCallback):
            def __init__(self):
                super().__init__(verbose=0)
                self.every_episodes = max(1, int(every_episodes))
                self.every_updates = max(1, int(every_updates))
                self.log_path = log_path
                self._t0 = time.time()
                self._n_envs = 0
                # 每个 env 一份：本局奖励分项、非法步数、已完成局窗口
                self._ep_comp: list[dict[str, float]] = []
                self._ep_invalid: list[int] = []
                self._window: list[dict[str, Any]] = []
                self._all_ok = 0
                self._all_ep = 0
                self._updates = 0
                self._fail_counts: dict[str, int] = defaultdict(int)

            def _log(self, line: str) -> None:
                print(line, flush=True)
                if self.log_path is not None:
                    with self.log_path.open("a", encoding="utf-8") as f:
                        f.write(line + "\n")

            def _on_training_start(self) -> None:
                self._n_envs = int(self.training_env.num_envs)
                self._ep_comp = [defaultdict(float) for _ in range(self._n_envs)]
                self._ep_invalid = [0] * self._n_envs
                self._log(
                    f"[train] start timesteps={cfg.TIMESTEPS} "
                    f"n_envs={self._n_envs} log_every_ep={self.every_episodes}"
                )

            def _on_step(self) -> bool:
                """每环境步：累加分项；若本局刚结束则写入窗口。"""
                infos = self.locals.get("infos") or []
                for i, info in enumerate(infos):
                    if not isinstance(info, dict):
                        continue
                    comps = info.get("reward_components") or {}
                    for k, v in comps.items():
                        try:
                            fv = float(v)
                        except (TypeError, ValueError):
                            continue
                        # 比率类只保留最后一步；加性奖励按局累加
                        if k in _LAST_ONLY_KEYS:
                            self._ep_comp[i][k] = fv
                        else:
                            self._ep_comp[i][k] += fv
                    if info.get("invalid"):
                        self._ep_invalid[i] += 1

                    # Monitor 只在 episode 结束时写入 info["episode"]
                    if "episode" not in info:
                        continue

                    mon = info["episode"] or {}
                    ep_r = float(mon.get("r", 0.0))
                    ep_l = int(mon.get("l", 0))
                    success = bool(info.get("success"))
                    fail = str(info.get("fail_reason") or ("ok" if success else "unknown"))
                    ep_id = str(info.get("episode_id") or "?")
                    placed = info.get("placed") or []
                    n_cards = int(info.get("n_cards") or 0)

                    self._window.append(
                        {
                            "reward": ep_r,
                            "length": ep_l,
                            "success": success,
                            "fail": fail,
                            "episode_id": ep_id,
                            "placed": len(placed),
                            "n_cards": n_cards,
                            "invalid_steps": self._ep_invalid[i],
                            "components": dict(self._ep_comp[i]),
                        }
                    )
                    self._all_ep += 1
                    self._all_ok += int(success)
                    if not success:
                        self._fail_counts[fail] += 1

                    self._ep_comp[i] = defaultdict(float)
                    self._ep_invalid[i] = 0

                    if len(self._window) >= self.every_episodes:
                        self._flush_window()
                return True

            def _flush_window(self) -> None:
                """把窗口内各局的成功率、分项均值打到控制台和 log。"""
                if not self._window:
                    return
                n = len(self._window)
                ok = sum(1 for r in self._window if r["success"])
                mean_r = sum(r["reward"] for r in self._window) / n
                mean_l = sum(r["length"] for r in self._window) / n
                mean_inv = sum(r["invalid_steps"] for r in self._window) / n
                elapsed = time.time() - self._t0
                fps = self.num_timesteps / max(1e-6, elapsed)

                comp_sum: dict[str, float] = defaultdict(float)
                for r in self._window:
                    for k, v in r["components"].items():
                        comp_sum[k] += float(v)
                comp_mean = {k: comp_sum[k] / n for k in comp_sum}

                fail_n: dict[str, int] = defaultdict(int)
                for r in self._window:
                    if not r["success"]:
                        fail_n[r["fail"]] += 1

                recent = self._window[-min(3, n) :]
                recent_s = ", ".join(
                    f"{r['episode_id']}:{'ok' if r['success'] else r['fail']}"
                    f"({r['placed']}/{r['n_cards'] or '?'})"
                    for r in recent
                )

                self._log(
                    f"[train:ep] steps={self.num_timesteps}/{cfg.TIMESTEPS} "
                    f"window={n} success={ok}/{n} ({ok / n:.0%}) "
                    f"all={self._all_ok}/{self._all_ep} "
                    f"({self._all_ok / max(1, self._all_ep):.0%}) "
                    f"mean_r={mean_r:.2f} mean_len={mean_l:.1f} "
                    f"mean_invalid={mean_inv:.2f} fps={fps:.0f}"
                )
                parts = " ".join(
                    f"{k}={comp_mean[k]:.2f}" for k in _REWARD_KEYS if k in comp_mean
                )
                if parts:
                    self._log(f"[train:reward] {parts}")
                blanks = [
                    r["components"]["blank_ratio"]
                    for r in self._window
                    if "blank_ratio" in r["components"]
                ]
                if blanks or fail_n:
                    blank_s = (
                        f"mean_blank={sum(blanks)/len(blanks):.2f} " if blanks else ""
                    )
                    self._log(
                        f"[train:terminal] {blank_s}fail_reasons={dict(fail_n) or {}}"
                    )
                self._log(f"[train:recent] {recent_s}")
                self._window.clear()

            def _on_rollout_end(self) -> None:
                """一次 PPO 更新结束：打印 loss / KL / explained_variance。"""
                self._updates += 1
                if self._updates % self.every_updates != 0:
                    return
                # 本轮 train/* 可能还没 dump；有值就打，没有就标 rollout_done
                keys = (
                    "rollout/ep_rew_mean",
                    "rollout/ep_len_mean",
                    "train/loss",
                    "train/policy_gradient_loss",
                    "train/value_loss",
                    "train/entropy_loss",
                    "train/approx_kl",
                    "train/clip_fraction",
                    "train/explained_variance",
                )
                vals = []
                logger = getattr(self.model, "logger", None)
                name_to_value = getattr(logger, "name_to_value", {}) if logger else {}
                for k in keys:
                    if k in name_to_value:
                        vals.append(f"{k.split('/', 1)[-1]}={name_to_value[k]:.4g}")
                if vals:
                    self._log(
                        f"[train:update] #{self._updates} steps={self.num_timesteps} "
                        + " ".join(vals)
                    )
                else:
                    self._log(
                        f"[train:update] #{self._updates} steps={self.num_timesteps} "
                        f"rollout_done (ppo metrics on next dump)"
                    )

            def _on_training_end(self) -> None:
                """冲掉窗口里剩下不足一轮的局，再打全训练成功率。"""
                self._flush_window()
                elapsed = time.time() - self._t0
                self._log(
                    f"[train] end steps={self.num_timesteps} "
                    f"episodes={self._all_ep} success={self._all_ok}/{self._all_ep} "
                    f"({self._all_ok / max(1, self._all_ep):.0%}) "
                    f"elapsed={elapsed:.0f}s fail_all={dict(self._fail_counts)}"
                )

        return _Callback()


def _load_eval_episodes(source: str):
    """解析评估用 episode 列表。

    输入:
        source: 同 data.load_episodes；"classic" 为 sample 中非 design- 子集。
    输出:
        episode dict 列表。
    """
    if source == "classic":
        return [
            ep
            for ep in load_episodes("sample")
            if not str(ep.get("id", "")).startswith("design-")
        ]
    if source == cfg.SOURCE:
        return load_training_episodes(source)
    return load_episodes(source)


def _has_complete_expert_layouts(episodes: list[dict[str, Any]]) -> bool:
    """全部验证页都有逐卡专家框时，专家质量指标才可用于选模。"""
    if not episodes:
        return False
    for ep in episodes:
        queue = ep.get("card_queue") or []
        experts = ep.get("expert_cards") or []
        if not queue or len(experts) != len(queue):
            return False
    return True


def _validation_quality_key(
    metrics: dict[str, Any],
    *,
    has_experts: bool = False,
) -> tuple[float, ...]:
    """验证选模：面积误差、成行率、空白率、1×1 数量，再看回报。"""
    del has_experts
    return (
        -float(metrics.get("mean_area_share_error") or 0.0),
        float(metrics.get("mean_row_band_rate") or 0.0),
        -float(metrics.get("mean_blank_rate") or 0.0),
        -float(metrics.get("mean_ones_count") or 0.0),
        float(metrics.get("mean_reward") or 0.0),
    )


def run_episode(
    model,
    env: LayoutEnv,
    *,
    episode: dict[str, Any] | None = None,
    seed: int | None = None,
    deterministic: bool = True,
) -> dict[str, Any]:
    """对单条 episode 做确定性（默认）rollout；训练评估与 test_model 共用。

    输入:
        model: MaskablePPO。
        env: LayoutEnv 实例。
        episode: 若给定则 reset(options={"episode": ...})；否则按 env.source 采样。
        seed / deterministic: 传给 reset / predict。
    输出:
        含 success、sequence、reward、placed、专家质量指标等字段的结果 dict。
    """
    options = {"episode": episode} if episode is not None else None
    obs, info0 = env.reset(seed=seed, options=options)
    done = False
    total_reward = 0.0
    info = info0
    step_hits: list[float] = []
    step_ious: list[float] = []
    step_l1: list[float] = []
    step_xy: list[float] = []
    step_wh: list[float] = []
    first_miss_step: int | None = None
    first_block_step: int | None = None
    step_i = 0

    while not done:
        masks = env.action_masks()
        if not masks.any():
            break
        action, _ = model.predict(
            obs, action_masks=masks, deterministic=deterministic
        )
        obs, reward, terminated, truncated, info = env.step(int(action))
        total_reward += float(reward)
        comps = info.get("reward_components") or {}
        if first_block_step is None and comps.get("packability_ok", 1.0) < 0.5:
            first_block_step = step_i
        card = None
        try:
            # step 后 cursor 已前进；用 placed 最后一张对齐 queue
            placed_now = info.get("placed") or list(env._placed)
            if placed_now:
                last = placed_now[-1]
                for q in env._queue:
                    if str(q.get("id")) == str(last.get("id")):
                        card = q
                        break
                if card is not None:
                    x, y, w, h = (
                        int(last["x"]),
                        int(last["y"]),
                        int(last["w"]),
                        int(last["h"]),
                    )
                    cols = int(env.cols)
                    rows = int(env.rows)
                    hit = annotation_exact_hit(x, y, w, h, card)
                    step_hits.append(1.0 if hit else 0.0)
                    step_ious.append(annotation_wh_iou_score(w, h, card))
                    step_l1.append(annotation_l1_error(x, y, w, h, card, cols, rows))
                    step_xy.append(
                        1.0 - annotation_xy_error(x, y, card, cols, rows)
                    )
                    step_wh.append(
                        1.0 - annotation_wh_error(w, h, card, cols, rows)
                    )
                    if first_miss_step is None and not hit:
                        first_miss_step = step_i
        except Exception:
            pass
        step_i += 1
        done = terminated or truncated

    placed = info.get("placed") or list(env._placed)
    n_scored = max(1, len(step_hits))
    exact_hit_rate = sum(step_hits) / n_scored if step_hits else 0.0
    mean_iou = sum(step_ious) / n_scored if step_ious else 0.0
    quality = layout_quality_metrics(
        placed,
        list(env._queue),
        int(env.cols),
        int(env.rows),
    )
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
        "exact_hit_rate": round(exact_hit_rate, 4),
        "mean_iou": round(mean_iou, 4),
        "mean_l1_error": round(sum(step_l1) / n_scored, 4) if step_l1 else None,
        "xy_hit_rate": round(sum(1 for v in step_xy if v >= 1.0 - 1e-9) / n_scored, 4)
        if step_xy
        else None,
        "wh_hit_rate": round(sum(1 for v in step_wh if v >= 1.0 - 1e-9) / n_scored, 4)
        if step_wh
        else None,
        "exact_episode": bool(step_hits) and all(v >= 1.0 for v in step_hits),
        "first_miss_step": first_miss_step,
        "first_block_step": first_block_step,
        **quality,
    }


def evaluate(
    model,
    *,
    source: str | None = None,
    episodes: int | None = None,
    label: str | None = None,
    dataset: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """确定性 rollout 评估成功率与专家质量指标。

    输出:
        dict: success_rate / mean_iou / exact_hit_rate / exact_episode_rate / ...
    """
    source = source or cfg.SOURCE
    if dataset is None:
        dataset = _load_eval_episodes(source)
    if episodes is not None:
        dataset = dataset[: max(1, episodes)]

    tag = label or source
    env = LayoutEnv(source="sample" if source == "classic" else source)
    ok = 0
    rewards: list[float] = []
    ious: list[float] = []
    hits: list[float] = []
    area_errs: list[float] = []
    row_bands: list[float] = []
    blanks: list[float] = []
    ones: list[float] = []
    exact_eps = 0
    no_legal = 0
    by_grid: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "n": 0,
            "ok": 0,
            "iou": 0.0,
            "hit": 0.0,
            "area": 0.0,
            "row": 0.0,
            "blank": 0.0,
            "ones": 0.0,
        }
    )
    print(f"[eval:{tag}] episodes -> {len(dataset)}")
    for i, ep in enumerate(dataset):
        result = run_episode(model, env, episode=ep, seed=cfg.SEED + i)
        success = bool(result["success"])
        ok += int(success)
        rewards.append(float(result.get("reward") or 0.0))
        if result.get("fail_reason") == "no_legal_moves":
            no_legal += 1
        iou = float(result.get("mean_iou") or 0.0)
        hit = float(result.get("exact_hit_rate") or 0.0)
        area_err = float(result.get("area_share_error") or 0.0)
        row_band = float(result.get("row_band_rate") or 0.0)
        blank = float(result.get("blank_rate") or 0.0)
        ones_n = float(result.get("ones_count") or 0.0)
        ious.append(iou)
        hits.append(hit)
        area_errs.append(area_err)
        row_bands.append(row_band)
        blanks.append(blank)
        ones.append(ones_n)
        if result.get("exact_episode"):
            exact_eps += 1
        gkey = f"{result.get('cols')}x{result.get('rows')}"
        by_grid[gkey]["n"] += 1
        by_grid[gkey]["ok"] += int(success)
        by_grid[gkey]["iou"] += iou
        by_grid[gkey]["hit"] += hit
        by_grid[gkey]["area"] += area_err
        by_grid[gkey]["row"] += row_band
        by_grid[gkey]["blank"] += blank
        by_grid[gkey]["ones"] += ones_n
        ep_id = result.get("episode_id")
        if success and result.get("sequence"):
            print(
                f"  ok  [{ep_id}] area={area_err:.2f} row={row_band:.0%} "
                f"blank={blank:.0%} ones={ones_n:.0f} {result['sequence']}"
            )
        else:
            print(
                f"  fail[{ep_id}] reason={result.get('fail_reason')} "
                f"placed={result.get('placed_n')}/{result.get('n_cards')} "
                f"area={area_err:.2f} row={row_band:.0%} blank={blank:.0%}"
            )
    n = max(1, len(dataset))
    rate = ok / n
    mean_reward = sum(rewards) / n
    mean_iou = sum(ious) / n
    mean_hit = sum(hits) / n
    mean_area = sum(area_errs) / n
    mean_row = sum(row_bands) / n
    mean_blank = sum(blanks) / n
    mean_ones = sum(ones) / n
    print(
        f"[eval:{tag}] success {ok}/{len(dataset)} ({rate:.0%}) "
        f"mean_reward={mean_reward:.3f} "
        f"area_err={mean_area:.3f} row_band={mean_row:.0%} "
        f"blank={mean_blank:.0%} ones={mean_ones:.2f} "
        f"no_legal={no_legal}"
    )
    for gkey, stats in sorted(by_grid.items()):
        gn = max(1, int(stats["n"]))
        print(
            f"  grid[{gkey}] n={gn} success={stats['ok']/gn:.0%} "
            f"area={stats['area']/gn:.3f} row={stats['row']/gn:.0%} "
            f"blank={stats['blank']/gn:.0%} ones={stats['ones']/gn:.2f}"
        )
    return {
        "success_rate": rate,
        "mean_reward": mean_reward,
        "mean_iou": mean_iou,
        "exact_hit_rate": mean_hit,
        "exact_episode_rate": exact_eps / n,
        "no_legal_rate": no_legal / n,
        "mean_area_share_error": mean_area,
        "mean_row_band_rate": mean_row,
        "mean_blank_rate": mean_blank,
        "mean_ones_count": mean_ones,
        "n": len(dataset),
        "by_grid": {
            k: {
                "n": int(v["n"]),
                "success_rate": v["ok"] / max(1, v["n"]),
                "mean_iou": v["iou"] / max(1, v["n"]),
                "exact_hit_rate": v["hit"] / max(1, v["n"]),
                "mean_area_share_error": v["area"] / max(1, v["n"]),
                "mean_row_band_rate": v["row"] / max(1, v["n"]),
                "mean_blank_rate": v["blank"] / max(1, v["n"]),
                "mean_ones_count": v["ones"] / max(1, v["n"]),
            }
            for k, v in by_grid.items()
        },
    }


def evaluate_after_train(
    model,
    val_eps: list[dict[str, Any]] | None = None,
) -> None:
    """训练结束后评估固定 held-out 与 EVAL_EXTRA_SOURCES。"""
    if getattr(cfg, "ONLINE_TRAIN", False):
        if val_eps:
            print("=" * 60)
            print("post-train eval: held-out synth val")
            evaluate(model, dataset=val_eps, label="val/split")
    else:
        print("=" * 60)
        print(f"post-train eval: train-set source={cfg.SOURCE!r}")
        evaluate(model, source=cfg.SOURCE, label=f"train/{cfg.SOURCE}")

    extras = getattr(cfg, "EVAL_EXTRA_SOURCES", ()) or ()
    for extra in extras:
        print("=" * 60)
        print(f"post-train eval: extra source={extra!r}")
        evaluate(model, source=extra, label=f"extra/{extra}")
    print("=" * 60)


def _write_model_meta(run_dir: Path) -> None:
    """保存观测契约与网络配置，供加载时校验。"""
    meta = {
        "obs_schema_version": OBS_SCHEMA_VERSION,
        "card_obs_dim": CARD_OBS_DIM,
        "spatial_channels": SPATIAL_CHANNELS,
        "layout_stats_dim": LAYOUT_STATS_DIM,
        "max_cols": cfg.MAX_COLS,
        "max_rows": cfg.MAX_ROWS,
        "max_cards": cfg.MAX_CARDS,
        "action_mode": "top_left_anchor_wh",
        "action_space_size": cfg.action_space_size(),
        "features_dim": cfg.FEATURES_DIM,
        "card_d_model": getattr(cfg, "CARD_D_MODEL", 128),
        "card_n_layers": getattr(cfg, "CARD_N_LAYERS", 3),
        "fuse_res_blocks": getattr(cfg, "FUSE_RES_BLOCKS", 2),
        "type_names": list(TYPE_NAMES),
        "ent_coef": cfg.ENT_COEF,
        "source": cfg.SOURCE,
    }
    path = run_dir / "model_meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved meta -> {path}")


def train() -> None:
    """完整训练管线：切数据 → VecEnv → learn → 存权重 → 评估。

    输出落在 ``Model/<时间戳>/``：final zip、可选 best zip、
    ``vecnormalize.pkl``、``model_meta.json``、``train_detail.log``。
    超参全部来自 config.py，这里只负责组装和跑。
    """
    try:
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    except ImportError as exc:
        raise SystemExit(
            "缺少依赖，请先: pip install -r RL/requirements.txt\n"
            f"原始错误: {exc}"
        ) from exc

    # 每次训练新建目录，避免覆盖上次权重和日志
    run_dir = cfg.new_run_dir()
    log_file = run_dir / "train_detail.log"
    updates = cfg.ppo_update_count()
    print("=" * 60)
    print(
        f"source={cfg.SOURCE!r} timesteps={cfg.TIMESTEPS} "
        f"(~{updates} PPO updates) n_envs={cfg.N_ENVS} seed={cfg.SEED}"
    )
    print(
        f"ppo: lr={cfg.LEARNING_RATE} n_steps={cfg.N_STEPS} "
        f"batch={cfg.BATCH_SIZE} n_epochs={cfg.N_EPOCHS} "
        f"gamma={cfg.GAMMA} gae_lambda={cfg.GAE_LAMBDA} clip={cfg.CLIP_RANGE}"
    )
    print(
        f"ppo: ent_coef={cfg.ENT_COEF} vf_coef={cfg.VF_COEF} "
        f"max_grad_norm={cfg.MAX_GRAD_NORM} target_kl={cfg.TARGET_KL} "
        f"features_dim={cfg.FEATURES_DIM} net_arch={cfg.NET_ARCH}"
    )
    print(
        f"obs_schema=v{OBS_SCHEMA_VERSION} "
        f"card_d_model={getattr(cfg, 'CARD_D_MODEL', 128)} "
        f"card_layers={getattr(cfg, 'CARD_N_LAYERS', 3)} "
        f"fuse_res={getattr(cfg, 'FUSE_RES_BLOCKS', 2)}"
    )
    print(
        f"layout_check={cfg.LAYOUT_CHECK_ENABLED} "
        f"url={cfg.LAYOUT_CHECK_URL} "
        f"growth_url={getattr(cfg, 'GRID_GROWTH_CHECK_URL', '')}"
    )
    print(f"run_dir -> {run_dir}")
    print(f"detail_log -> {log_file}")
    print(f"post-eval extras -> {getattr(cfg, 'EVAL_EXTRA_SOURCES', ())}")
    print(
        f"log_every_episodes={getattr(cfg, 'TRAIN_LOG_EVERY_EPISODES', 20)} "
        f"log_every_updates={getattr(cfg, 'TRAIN_LOG_EVERY_UPDATES', 1)}"
    )
    print("=" * 60)

    # ----- 数据：在线抽样训练；synth 只作固定 val -----
    heldout = load_training_episodes(cfg.SOURCE)
    _train_eps, val_eps = split_episodes_by_grid(
        heldout,
        val_ratio=float(getattr(cfg, "VAL_RATIO", 0.15)),
        seed=cfg.SEED,
    )
    if getattr(cfg, "ONLINE_TRAIN", False):
        print(
            f"[data] online random sequences; "
            f"held-out val={len(val_eps)} from {cfg.SOURCE!r}"
        )
        factory = make_env(source="random")
    else:
        grid = getattr(cfg, "TRAIN_GRID", None)
        grid_label = f"{grid[0]}x{grid[1]}" if grid else "any"
        ids = ", ".join(str(ep.get("id")) for ep in heldout)
        print(f"[data] train_grid={grid_label} episodes={len(heldout)} ids={ids}")
        audit_observation_aliasing(heldout, warn=True)
        print(f"[data:split] train={len(_train_eps)} val={len(val_eps)}")
        factory = make_env(_train_eps)

    # ----- 环境：N_ENVS 路并行 -----
    venv = DummyVecEnv([factory for _ in range(cfg.N_ENVS)])
    if getattr(cfg, "NORMALIZE_REWARD", False):
        venv = VecNormalize(
            venv,
            norm_obs=False,
            norm_reward=True,
            clip_reward=10.0,
            gamma=cfg.GAMMA,
        )
    model = build_model(venv)

    if getattr(cfg, "BC_PRETRAIN", False):
        print("=" * 60)
        print(
            f"[teacher] beam={getattr(cfg, 'TEACHER_BEAM_WIDTH', 8)} "
            f"episodes={getattr(cfg, 'BC_EPISODES', 200)}"
        )
        transitions = collect_teacher_transitions(
            n_episodes=int(getattr(cfg, "BC_EPISODES", 200)),
            beam_width=int(getattr(cfg, "TEACHER_BEAM_WIDTH", 8)),
            seed=int(cfg.SEED),
        )
        behavior_clone(
            model,
            transitions,
            epochs=int(getattr(cfg, "BC_EPOCHS", 8)),
            batch_size=int(getattr(cfg, "BC_BATCH_SIZE", 64)),
        )
        bc_path = run_dir / "layout_maskable_ppo_bc"
        model.save(str(bc_path))
        print(f"[bc] saved -> {bc_path}.zip")

    from stable_baselines3.common.callbacks import BaseCallback, CallbackList

    class ValQualityCallback(BaseCallback):
        """自写的验证回调，角色对应官方 ``EvalCallback``。

        按面积误差、成行率、空白率、1×1 数量、回报选 best。

        触发点在 ``_on_rollout_end``（一次 PPO update 结束），不是每步。
        ``VAL_EVERY_UPDATES`` 默认 20，约每 20 次更新评一轮。
        """

        def __init__(self, val_episodes: list[dict[str, Any]], run_dir: Path):
            super().__init__(verbose=0)
            self.val_episodes = val_episodes
            self.run_dir = run_dir
            self.every = max(1, int(getattr(cfg, "VAL_EVERY_UPDATES", 20)))
            self.has_experts = _has_complete_expert_layouts(val_episodes)
            self.best_quality: tuple[float, ...] | None = None
            self._updates = 0

        def _on_step(self) -> bool:
            # SB3 每环境步都会调；选 best 放在 rollout 结束，这里保持继续训练
            return True

        def _on_rollout_end(self) -> None:
            """缓冲采满并完成一次 PPO 更新后：够间隔则跑 val，IoU 更好则存盘。"""
            self._updates += 1
            if not self.val_episodes or self._updates % self.every != 0:
                return
            # 评估轨迹不要写进 VecNormalize 的 running 均值；评完再恢复
            training = True
            if hasattr(self.model.get_env(), "training"):
                training = bool(self.model.get_env().training)
                self.model.get_env().training = False
            try:
                metrics = evaluate(
                    self.model,
                    dataset=self.val_episodes,
                    label=f"val@{self._updates}",
                )
            finally:
                if hasattr(self.model.get_env(), "training"):
                    self.model.get_env().training = training
            quality = _validation_quality_key(
                metrics,
                has_experts=self.has_experts,
            )
            if self.best_quality is None or quality > self.best_quality:
                self.best_quality = quality
                best = self.run_dir / getattr(
                    cfg, "BEST_CHECKPOINT_NAME", "layout_maskable_ppo_best"
                )
                self.model.save(str(best))
                print(
                    f"[val:best] update={self._updates} "
                    f"area_err={metrics.get('mean_area_share_error', 0):.3f} "
                    f"row_band={metrics.get('mean_row_band_rate', 0):.0%} "
                    f"blank={metrics.get('mean_blank_rate', 0):.0%} "
                    f"ones={metrics.get('mean_ones_count', 0):.2f} "
                    f"mean_reward={metrics.get('mean_reward', 0):.3f} "
                    f"-> {best}.zip",
                    flush=True,
                )

    # 日志回调 + 验证集选 best，一起交给 learn
    detail_cb = TrainDetailCallback.create(
        every_episodes=getattr(cfg, "TRAIN_LOG_EVERY_EPISODES", 20),
        every_updates=getattr(cfg, "TRAIN_LOG_EVERY_UPDATES", 1),
        log_path=log_file,
    )
    callbacks = CallbackList(
        [detail_cb, ValQualityCallback(val_eps, run_dir)]
    )
    # 步数是环境交互次数，不是 SGD epoch；约 updates = TIMESTEPS / (N_STEPS * N_ENVS)
    model.learn(
        total_timesteps=cfg.TIMESTEPS,
        progress_bar=True,
        callback=callbacks,
    )

    # ----- 收尾：final 权重、归一化统计、观测契约，再跑评估 -----
    out = cfg.checkpoint_path(run_dir)
    model.save(str(out))
    print(f"saved model -> {out}.zip")
    if getattr(cfg, "NORMALIZE_REWARD", True):
        # 推理时必须用同一套 VecNormalize 统计，否则奖励尺度对不上
        venv.save(str(run_dir / "vecnormalize.pkl"))
    _write_model_meta(run_dir)
    evaluate_after_train(model, val_eps=val_eps)
    if val_eps and not getattr(cfg, "ONLINE_TRAIN", False):
        print("=" * 60)
        print("post-train eval: held-out val split")
        evaluate(model, dataset=val_eps, label="val/split")
        print("=" * 60)


def main() -> None:
    train()


if __name__ == "__main__":
    main()
