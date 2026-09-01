"""布局还原 Gym 环境：状态机薄封装，细节在 layout/reward。

一局 episode = 固定顺序放置 N 张卡；每步 agent 选择 (x,y,w,h)。
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError as exc:  # pragma: no cover
    raise ImportError("需要 gymnasium: pip install gymnasium") from exc

from . import config as cfg
from .data import load_episodes
from .layout import (
    action_masks,
    build_obs,
    can_place,
    cards_from_episode,
    decode_action,
    density,
    greedy_packable,
    place,
    to_sequence,
)
from .reward import (
    fail_reward,
    legality_reward,
    packability_penalty,
    style_reward,
    success_reward,
)


class LayoutEnv(gym.Env):
    """顺序网格布局 Gym 环境（MaskablePPO 兼容）。

    观测: Dict(occupancy, current_card, remaining, grid, progress)。
    动作: Discrete，编码 (x,y,w,h)；合法子集由 action_masks() 给出。
    奖励: 见 reward.py；step 返回 info["reward_components"] 便于调试。

    终止条件:
        terminated — 全部卡放置成功。
        truncated  — 连续非法达上限 / 无合法动作 / 非法 streak。
    """

    metadata = {"render_modes": ["ansi"], "name": "LayoutEnv-v1"}

    def __init__(
        self,
        *,
        source: Optional[str] = None,
        seed: Optional[int] = None,
        render_mode: Optional[str] = None,
    ) -> None:
        """初始化环境；非 random 源会预加载 dataset 与采样权重。

        输入:
            source: 数据别名（design/sample/random/both）或 jsonl 路径。
            seed: numpy RNG 种子，影响 episode 采样与 random 布局。
            render_mode: "ansi" 时 render() 输出 ASCII 棋盘。
        """
        super().__init__()
        self.source = source or cfg.SOURCE
        self.max_cols = cfg.MAX_COLS
        self.max_rows = cfg.MAX_ROWS
        self.max_card_w = cfg.MAX_CARD_W
        self.max_card_h = cfg.MAX_CARD_H
        self.max_cards = cfg.MAX_CARDS
        self.max_invalid_streak = cfg.MAX_INVALID_STREAK
        self.r_valid = cfg.LEGAL_VALID_REWARD
        self.r_invalid = cfg.LEGAL_INVALID_PENALTY
        self.r_success = cfg.REWARD_SUCCESS
        self.r_fail = cfg.REWARD_FAIL
        self.r_density = cfg.REWARD_DENSITY
        self.r_style_edge = cfg.STYLE_EDGE_WEIGHT
        self.r_style_alignment = cfg.STYLE_ALIGNMENT_WEIGHT
        self.r_style_parallel = cfg.STYLE_PARALLEL_WEIGHT
        self.r_style_order = cfg.STYLE_ORDER_WEIGHT
        self.r_style_origin = cfg.STYLE_ORIGIN_WEIGHT
        self.r_style_prev_adjacent = cfg.STYLE_PREV_ADJACENT_WEIGHT
        self.r_imitation = cfg.IMITATION_WEIGHT
        self.r_packability = cfg.PACKABILITY_PENALTY
        self.style_similarity_threshold = cfg.STYLE_SIMILARITY_THRESHOLD
        self.hard_min_cards = cfg.HARD_EPISODE_MIN_CARDS
        self.hard_weight = cfg.HARD_EPISODE_WEIGHT
        self.render_mode = render_mode

        self.action_space = spaces.Discrete(
            cfg.action_space_size(
                self.max_cols,
                self.max_rows,
                self.max_card_w,
                self.max_card_h,
            )
        )
        self.observation_space = spaces.Dict(
            {
                "occupancy": spaces.Box(
                    0, 1, (self.max_rows, self.max_cols), np.float32
                ),
                "current_card": spaces.Box(0, 1, (4,), np.float32),
                "remaining": spaces.Box(0, 1, (self.max_cards, 2), np.float32),
                "grid": spaces.Box(0, 1, (2,), np.float32),
                "progress": spaces.Box(0, 1, (2,), np.float32),
            }
        )

        self._dataset: list[dict[str, Any]] = []
        self._sample_weights: Optional[np.ndarray] = None
        if self.source != "random":
            self._dataset = load_episodes(self.source)
            self._sample_weights = self._build_sample_weights(self._dataset)

        self._rng = np.random.default_rng(seed)
        self.cols = self.rows = 0
        self._queue: list[dict[str, Any]] = []
        self._placed: list[dict[str, Any]] = []
        self._occ = np.zeros((self.max_rows, self.max_cols), dtype=np.int8)
        self._cursor = 0
        self._invalid_streak = 0
        self._episode_id = ""
        self._total_cards = 0

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        """开始新一局，清空占用与放置记录。

        输入:
            options["episode"]: 直接使用指定 episode dict。
            options["episode_id"]: 从 dataset 按 id 查找。
            否则按 source 加权采样或 random 生成。
        输出:
            (obs, info)；info 含 episode_id, cols, rows, n_cards, action_mask。
        """
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._occ.fill(0)
        self._placed = []
        self._cursor = 0
        self._invalid_streak = 0

        options = options or {}
        if "episode" in options:
            self._load_episode(options["episode"])
        elif "episode_id" in options:
            ep = next(e for e in self._dataset if e["id"] == options["episode_id"])
            self._load_episode(ep)
        elif self.source == "random" or (
            self.source == "both" and self._rng.random() >= 0.7
        ):
            self._load_random()
        else:
            self._load_episode(self._sample_episode())

        info = {
            "episode_id": self._episode_id,
            "cols": self.cols,
            "rows": self.rows,
            "n_cards": self._total_cards,
            "action_mask": self.action_masks(),
        }
        return self._obs(), info

    def step(self, action: int):
        """执行一步放置动作。

        输入:
            action: 离散 id，decode 为 (x,y,w,h)。
        输出:
            (obs, reward, terminated, truncated, info)。
        逻辑:
            1) 非法 → legality 惩罚；streak 达上限则 fail_reward 并 truncated。
            2) 合法 → legality + style + packability；放满则 success_reward + terminated。
            3) 合法但下一张无合法动作 → fail_reward + truncated。
        """
        card = self._current()
        info: dict[str, Any] = {
            "episode_id": self._episode_id,
            "invalid": False,
            "success": False,
        }
        if card is None:
            return self._obs(), 0.0, True, False, {**info, "success": True}

        x, y, w, h = decode_action(
            int(action), self.max_cols, self.max_card_w, self.max_card_h
        )
        if not can_place(self._occ, x, y, w, h, self.cols, self.rows):
            self._invalid_streak += 1
            legal = legality_reward(False, self.r_valid, self.r_invalid)
            terminal_reward = 0.0
            reward = legal
            truncated = False
            if self._invalid_streak >= self.max_invalid_streak:
                leftover = self._total_cards - self._cursor
                terminal_reward = fail_reward(
                    self.r_fail, leftover, self._total_cards
                )
                reward += terminal_reward
                truncated = True
                info["fail_reason"] = "invalid_streak"
            info["invalid"] = True
            info["reward_components"] = {
                "legality": legal,
                "style": 0.0,
                "terminal": terminal_reward,
            }
            info["action_mask"] = self.action_masks()
            return self._obs(), float(reward), False, truncated, info

        self._invalid_streak = 0
        legal = legality_reward(True, self.r_valid, self.r_invalid)
        placed_card = {**card, "w": w, "h": h}
        style, style_details = style_reward(
            placed_card,
            x,
            y,
            self._placed,
            cols=self.cols,
            rows=self.rows,
            cursor=self._cursor,
            total_cards=self._total_cards,
            edge_weight=self.r_style_edge,
            alignment_weight=self.r_style_alignment,
            parallel_weight=self.r_style_parallel,
            order_weight=self.r_style_order,
            origin_weight=self.r_style_origin,
            imitation_weight=self.r_imitation,
            prev_adjacent_weight=self.r_style_prev_adjacent,
            similarity_threshold=self.style_similarity_threshold,
        )
        place(self._occ, x, y, w, h)
        self._placed.append(
            {"id": card["id"], "w": w, "h": h, "x": x, "y": y}
        )
        self._cursor += 1

        remaining = self._queue[self._cursor :]
        packable = greedy_packable(self._occ, remaining, self.cols, self.rows)
        pack_pen = packability_penalty(packable, self.r_packability)
        reward = legal + style + pack_pen
        style_details = {**style_details, "packable": float(packable)}

        terminated = truncated = False
        terminal_reward = 0.0
        if self._cursor >= self._total_cards:
            terminated = True
            info["success"] = True
            dens = density(self._occ, self.cols, self.rows)
            terminal_reward = success_reward(self.r_success, self.r_density, dens)
            reward += terminal_reward
            info["sequence"] = to_sequence(self._placed)
            info["placed"] = list(self._placed)
            info["density"] = dens
        elif not self.action_masks().any():
            leftover = self._total_cards - self._cursor
            terminal_reward = fail_reward(self.r_fail, leftover, self._total_cards)
            reward += terminal_reward
            truncated = True
            info["fail_reason"] = "no_legal_moves"
            info["placed"] = list(self._placed)

        info["reward_components"] = {
            "legality": legal,
            "style": style,
            "packability": pack_pen,
            "terminal": terminal_reward,
            **style_details,
        }
        info["action_mask"] = self.action_masks()
        return self._obs(), float(reward), terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """返回当前步合法动作的 bool 掩码（MaskablePPO 必需）。

        输出:
            长度 action_space.n；全 False 表示无卡可放或无可行 (x,y,w,h)。
        """
        if self._current() is None:
            return np.zeros(
                cfg.action_space_size(
                    self.max_cols,
                    self.max_rows,
                    self.max_card_w,
                    self.max_card_h,
                ),
                dtype=bool,
            )
        return action_masks(
            self._occ,
            self.cols,
            self.rows,
            self.max_cols,
            self.max_rows,
            self.max_card_w,
            self.max_card_h,
        )

    def get_layout_sequence(self) -> str:
        """已放置卡的 (w,h,x,y) 序列字符串。"""
        return to_sequence(self._placed)

    def render(self):
        """ANSI 棋盘：每格一个字符表示卡序号（hex）。"""
        if self.render_mode != "ansi":
            return None
        board = np.full((self.rows, self.cols), ".", dtype=object)
        for i, p in enumerate(self._placed):
            ch = format(i % 16, "X")
            board[p["y"] : p["y"] + p["h"], p["x"] : p["x"] + p["w"]] = ch
        head = f"grid={self.cols}x{self.rows} placed={len(self._placed)}/{self._total_cards}"
        return head + "\n" + "\n".join("".join(row) for row in board)

    def _obs(self) -> dict[str, np.ndarray]:
        """委托 layout.build_obs 拼装观测。"""
        return build_obs(
            occ=self._occ,
            queue=self._queue,
            cursor=self._cursor,
            cols=self.cols,
            rows=self.rows,
            max_cols=self.max_cols,
            max_rows=self.max_rows,
            max_cards=self.max_cards,
            total_cards=self._total_cards,
        )

    def _current(self) -> Optional[dict[str, Any]]:
        """队列中 cursor 指向的待放置卡；放完返回 None。"""
        if self._cursor >= len(self._queue):
            return None
        return self._queue[self._cursor]

    def _build_sample_weights(self, episodes: list[dict[str, Any]]) -> np.ndarray:
        """难例加权：卡数多或 tablet 布局提高采样概率。

        输出:
            归一化权重数组，长度 len(episodes)。
        """
        weights = np.ones(len(episodes), dtype=np.float64)
        for i, ep in enumerate(episodes):
            n = int(ep.get("n_cards", len(ep.get("cards_wh", []))))
            ep_id = str(ep.get("id", ""))
            if n >= self.hard_min_cards or "tablet" in ep_id:
                weights[i] = self.hard_weight
        weights /= weights.sum()
        return weights

    def _sample_episode(self) -> dict[str, Any]:
        """按 _sample_weights 随机抽一条 dataset episode。"""
        if not self._dataset:
            raise RuntimeError("empty dataset")
        if self._sample_weights is None:
            idx = int(self._rng.integers(0, len(self._dataset)))
        else:
            idx = int(self._rng.choice(len(self._dataset), p=self._sample_weights))
        return self._dataset[idx]

    def _load_episode(self, ep: dict[str, Any]) -> None:
        """从 episode dict 初始化画布尺寸与卡片队列。"""
        self.cols = int(ep["grid"]["cols"])
        self.rows = int(ep["grid"]["rows"])
        self._queue = cards_from_episode(ep)
        self._episode_id = str(ep.get("id", "dataset"))
        self._total_cards = len(self._queue)

    def _load_random(self) -> None:
        """程序化生成随机可放下的卡片集合（无专家坐标）。"""
        from .tools.generate_episode_cards import generate_episode_cards

        choices = [(6, 13), (8, 12), (16, 10), (10, 10)]
        self.cols, self.rows = choices[int(self._rng.integers(0, len(choices)))]
        items = generate_episode_cards(
            cols=self.cols,
            rows=self.rows,
            seed=int(self._rng.integers(0, 1_000_000_000)),
        )[: self.max_cards]
        cards = [
            {
                "id": f"c{i}",
                "suggest_w": int(it.w),
                "suggest_h": int(it.h),
                "expert_w": int(it.w),
                "expert_h": int(it.h),
                "expert_x": None,
                "expert_y": None,
            }
            for i, it in enumerate(items)
            if it.w <= self.cols and it.h <= self.rows
        ] or [
            {
                "id": "c0",
                "suggest_w": 1,
                "suggest_h": 1,
                "expert_w": 1,
                "expert_h": 1,
                "expert_x": None,
                "expert_y": None,
            }
        ]
        self._queue = cards
        self._episode_id = "random"
        self._total_cards = len(self._queue)
