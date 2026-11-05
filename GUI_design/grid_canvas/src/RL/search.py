"""布局搜索：精确 Beam / 策略引导 Beam，以及行为克隆。

不改动作空间。老师用当前奖励做搜索，推理时用策略概率收窄分支。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import config as cfg
from .env import LayoutEnv
from .reward import layout_quality_metrics


@dataclass
class SearchNode:
    snap: dict[str, Any]
    reward: float
    actions: list[int]
    done: bool = False
    success: bool = False
    info: dict[str, Any] = field(default_factory=dict)


def env_snapshot(env: LayoutEnv) -> dict[str, Any]:
    """只保存一局内会变的棋盘状态。"""
    return {
        "occ": env._occ.copy(),
        "placed": [dict(card) for card in env._placed],
        "cursor": int(env._cursor),
        "invalid_streak": int(env._invalid_streak),
    }


def env_restore(env: LayoutEnv, snap: dict[str, Any]) -> None:
    env._occ[:] = snap["occ"]
    env._placed = [dict(card) for card in snap["placed"]]
    env._cursor = int(snap["cursor"])
    env._invalid_streak = int(snap["invalid_streak"])


def replay_actions(
    env: LayoutEnv,
    episode: dict[str, Any],
    actions: list[int],
) -> list[dict[str, Any]]:
    """从 reset 重放动作，收集 (obs, mask, action) 供行为克隆。"""
    obs, _ = env.reset(options={"episode": episode})
    transitions: list[dict[str, Any]] = []
    for action in actions:
        mask = env.action_masks()
        transitions.append(
            {
                "obs": {key: value.copy() for key, value in obs.items()},
                "mask": mask.copy(),
                "action": int(action),
            }
        )
        obs, _reward, terminated, truncated, _info = env.step(int(action))
        if terminated or truncated:
            break
    return transitions


def _legal_actions(mask: np.ndarray) -> list[int]:
    return [int(action) for action in np.flatnonzero(mask)]


def _policy_candidates(
    policy,
    obs: dict[str, np.ndarray],
    mask: np.ndarray,
    top_k: int | None,
) -> list[int]:
    legal = _legal_actions(mask)
    if not legal:
        return []
    if policy is None or top_k is None or top_k >= len(legal):
        return legal
    import torch
    from stable_baselines3.common.utils import obs_as_tensor

    batched = {key: np.expand_dims(value, 0) for key, value in obs.items()}
    with torch.no_grad():
        obs_t = obs_as_tensor(batched, policy.device)
        mask_t = torch.as_tensor(np.expand_dims(mask, 0), device=policy.device)
        dist = policy.get_distribution(obs_t, action_masks=mask_t)
        probs = dist.distribution.probs[0].detach().cpu().numpy()
    legal.sort(key=lambda action: float(probs[action]), reverse=True)
    return legal[: max(1, int(top_k))]


def beam_search(
    env: LayoutEnv,
    episode: dict[str, Any],
    *,
    beam_width: int = 8,
    policy=None,
    policy_top_k: int | None = None,
) -> dict[str, Any]:
    """对一页做 Beam Search，按累计奖励保留宽度 ``beam_width``。

    无策略时展开全部合法动作；有策略时只展开概率最高的 ``policy_top_k`` 个。
    """
    env.reset(options={"episode": episode})
    beam = [
        SearchNode(snap=env_snapshot(env), reward=0.0, actions=[]),
    ]
    finished: list[SearchNode] = []
    width = max(1, int(beam_width))

    while beam:
        nxt: list[SearchNode] = []
        for node in beam:
            env_restore(env, node.snap)
            mask = env.action_masks()
            if not mask.any():
                finished.append(
                    SearchNode(
                        snap=node.snap,
                        reward=node.reward,
                        actions=list(node.actions),
                        done=True,
                        success=False,
                        info={"fail_reason": "no_legal_moves"},
                    )
                )
                continue
            obs = env._obs()
            for action in _policy_candidates(policy, obs, mask, policy_top_k):
                env_restore(env, node.snap)
                _obs, reward, terminated, truncated, info = env.step(int(action))
                nxt.append(
                    SearchNode(
                        snap=env_snapshot(env),
                        reward=node.reward + float(reward),
                        actions=node.actions + [int(action)],
                        done=bool(terminated or truncated),
                        success=bool(info.get("success")),
                        info=info,
                    )
                )
        live = [node for node in nxt if not node.done]
        finished.extend(node for node in nxt if node.done)
        live.sort(key=lambda node: node.reward, reverse=True)
        beam = live[:width]

    if not finished:
        env.reset(options={"episode": episode})
        return _empty_search_result(env, episode)

    best = max(finished, key=lambda node: (int(node.success), node.reward))
    env.reset(options={"episode": episode})
    info: dict[str, Any] = {}
    for action in best.actions:
        _obs, _reward, _term, _trunc, info = env.step(int(action))
    return _search_result(env, episode, best, info)


def policy_beam_search(
    model,
    env: LayoutEnv,
    episode: dict[str, Any],
    *,
    beam_width: int | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """推理用：用策略概率收窄的 Beam Search。"""
    policy = getattr(model, "policy", model)
    return beam_search(
        env,
        episode,
        beam_width=beam_width or int(getattr(cfg, "INFER_BEAM_WIDTH", 8)),
        policy=policy,
        policy_top_k=top_k if top_k is not None else int(
            getattr(cfg, "INFER_POLICY_TOP_K", 4)
        ),
    )


def _empty_search_result(env: LayoutEnv, episode: dict[str, Any]) -> dict[str, Any]:
    quality = layout_quality_metrics([], env._queue, env.cols, env.rows)
    return {
        "episode_id": episode.get("id"),
        "success": False,
        "fail_reason": "no_legal_moves",
        "n_cards": len(env._queue),
        "placed_n": 0,
        "cols": env.cols,
        "rows": env.rows,
        "reward": 0.0,
        "sequence": env.get_layout_sequence(),
        "placed": [],
        "actions": [],
        **quality,
    }


def _search_result(
    env: LayoutEnv,
    episode: dict[str, Any],
    node: SearchNode,
    info: dict[str, Any],
) -> dict[str, Any]:
    placed = info.get("placed") or list(env._placed)
    quality = layout_quality_metrics(placed, env._queue, env.cols, env.rows)
    return {
        "episode_id": info.get("episode_id") or episode.get("id"),
        "success": bool(node.success or info.get("success")),
        "fail_reason": info.get("fail_reason"),
        "n_cards": len(env._queue),
        "placed_n": len(placed),
        "cols": env.cols,
        "rows": env.rows,
        "reward": round(float(node.reward), 4),
        "sequence": info.get("sequence") or env.get_layout_sequence(),
        "placed": placed,
        "actions": list(node.actions),
        **quality,
    }


def collect_teacher_transitions(
    *,
    n_episodes: int,
    beam_width: int,
    seed: int,
    env: LayoutEnv | None = None,
) -> list[dict[str, Any]]:
    """在线生成页面，用 Beam Search 求高分轨迹。"""
    from .tools.gen_random_grids import generate_episodes

    env = env or LayoutEnv(source="random", seed=seed)
    episodes = generate_episodes(int(n_episodes), int(seed))
    transitions: list[dict[str, Any]] = []
    ok = 0
    for i, episode in enumerate(episodes):
        result = beam_search(env, episode, beam_width=beam_width)
        if result.get("success") and result.get("actions"):
            ok += 1
            transitions.extend(replay_actions(env, episode, result["actions"]))
        if (i + 1) % 20 == 0 or i + 1 == len(episodes):
            print(
                f"[teacher] {i + 1}/{len(episodes)} "
                f"success={ok} transitions={len(transitions)}",
                flush=True,
            )
    return transitions


def behavior_clone(
    model,
    transitions: list[dict[str, Any]],
    *,
    epochs: int,
    batch_size: int,
) -> None:
    """用老师动作对 MaskablePPO 策略做交叉熵预训练。"""
    if not transitions:
        print("[bc] skip: empty teacher set", flush=True)
        return
    import torch
    from stable_baselines3.common.utils import obs_as_tensor

    policy = model.policy
    policy.train()
    n = len(transitions)
    batch = max(1, int(batch_size))
    print(
        f"[bc] transitions={n} epochs={epochs} batch={batch}",
        flush=True,
    )
    for epoch in range(int(epochs)):
        order = np.random.permutation(n)
        total = 0.0
        steps = 0
        for start in range(0, n, batch):
            chunk = [transitions[int(i)] for i in order[start : start + batch]]
            obs = {
                key: np.stack([item["obs"][key] for item in chunk])
                for key in chunk[0]["obs"]
            }
            masks = np.stack([item["mask"] for item in chunk])
            actions = np.asarray([item["action"] for item in chunk], dtype=np.int64)
            obs_t = obs_as_tensor(obs, policy.device)
            mask_t = torch.as_tensor(masks, device=policy.device)
            action_t = torch.as_tensor(actions, device=policy.device)
            dist = policy.get_distribution(obs_t, action_masks=mask_t)
            loss = -dist.log_prob(action_t).mean()
            policy.optimizer.zero_grad()
            loss.backward()
            policy.optimizer.step()
            total += float(loss.detach().cpu())
            steps += 1
        print(
            f"[bc] epoch={epoch + 1}/{epochs} loss={total / max(1, steps):.4f}",
            flush=True,
        )
