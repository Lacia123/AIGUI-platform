"""布局还原 Gym 环境：状态机薄封装，几何在 layout，奖励在 reward。

一局 episode = 固定顺序放置 N 张卡；每步 agent 只选择 (w,h)。
位置由「左上空白锚点」确定，不进动作空间。

SB3 / MaskablePPO 只认本文件的 Gym 接口：
  reset / step / observation_space / action_space / action_masks
网络结构不在这里，见 policy.py 的 LayoutFeaturesExtractor。
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
from .card_types import (
    CARD_OBS_DIM,
    LAYOUT_STATS_DIM,
    SPATIAL_CHANNELS,
    TYPE_VOCAB,
    type_min_area,
)
from .data import load_episodes, load_training_episodes, validate_episode
from .layout import (
    action_masks,
    anchored_box,
    aspect_ratio_ok,
    build_obs,
    can_place,
    cards_from_episode,
    decode_action,
    density,
    place,
    top_left_empty_anchor,
    to_sequence,
)
from .reward import compute_reward


class LayoutEnv(gym.Env):
    """顺序网格布局 Gym 环境（MaskablePPO 兼容）。

    观测 Dict:
        spatial  — (7, MAX_ROWS, MAX_COLS) 占用与锚点等通道
        cards    — (MAX_CARDS, CARD_OBS_DIM) 队列特征（无专家几何答案）
        grid     — 画布级统计
        cursor   — 当前放到第几张（归一化）
    动作:
        Discrete，只编码 (w,h)；x,y 由 top_left_empty_anchor 决定。
    奖励:
        step 末尾调用 reward.compute_reward；分项进 info["reward_components"]。

    终止:
        terminated — 全部卡放完（成功）
        truncated  — 连续非法达上限，或下一步无合法 (w,h)
    """

    metadata = {"render_modes": ["ansi"], "name": "LayoutEnv-v1"}

    def __init__(
        self,
        *,
        source: Optional[str] = None,
        episodes: Optional[list[dict[str, Any]]] = None,
        seed: Optional[int] = None,
        render_mode: Optional[str] = None,
    ) -> None:
        """初始化空间定义，并按 source 预加载 dataset / 采样权重。

        输入:
            source: 数据别名或 jsonl 路径；默认 cfg.SOURCE（当前多为 synth）。
            episodes: 可选的预加载 episode 子集；训练时用于隔离 train/val。
            seed: numpy RNG，影响加权采样与 random 布局。
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
        # 训练采样加权（难例 / 稀有网格等），与奖励无关
        self.hard_min_cards = cfg.HARD_EPISODE_MIN_CARDS
        self.hard_weight = cfg.HARD_EPISODE_WEIGHT
        self.rare_grid_weight = cfg.RARE_GRID_WEIGHT
        self.rare_grid_sqrt = getattr(cfg, "RARE_GRID_SQRT", True)
        self.rare_grid_cap = float(getattr(cfg, "RARE_GRID_WEIGHT_CAP", 5.0))
        self.same_type_varied_weight = float(
            getattr(cfg, "SAME_TYPE_VARIED_WEIGHT", 2.0)
        )
        self.no_legal_ids = set(getattr(cfg, "NO_LEGAL_MOVES_EPISODE_IDS", ()))
        self.no_legal_weight = float(getattr(cfg, "NO_LEGAL_MOVES_WEIGHT", 2.0))
        self.hard_size_ids = set(getattr(cfg, "HARD_SIZE_EPISODE_IDS", ()))
        self.hard_size_weight = float(getattr(cfg, "HARD_SIZE_WEIGHT", 1.0))
        self.render_mode = render_mode

        # ----- Gym 空间：SB3 据此建网络输入/输出维 -----
        # 动作 n = MAX_CARD_W * MAX_CARD_H，例如 8*6=48
        self.action_space = spaces.Discrete(
            cfg.action_space_size(self.max_card_w, self.max_card_h)
        )
        self.observation_space = spaces.Dict(
            {
                "spatial": spaces.Box(
                    0, 1, (SPATIAL_CHANNELS, self.max_rows, self.max_cols), np.float32
                ),
                "cards": spaces.Box(
                    0,
                    float(max(TYPE_VOCAB - 1, 2)),
                    (self.max_cards, CARD_OBS_DIM),
                    np.float32,
                ),
                "grid": spaces.Box(0, 1, (LAYOUT_STATS_DIM,), np.float32),
                "cursor": spaces.Box(0, 1, (1,), np.float32),
            }
        )

        # ----- 数据：非 random 时预读 jsonl，供 reset 加权采样 -----
        self._dataset: list[dict[str, Any]] = []
        self._sample_weights: Optional[np.ndarray] = None
        if episodes is not None:
            if self.source == "random":
                raise ValueError("source='random' 不能同时传 episodes")
            if not episodes:
                raise ValueError("episodes 不能为空")
            self._dataset = list(episodes)
            self._sample_weights = self._build_sample_weights(self._dataset)
        elif self.source != "random":
            self._dataset = (
                load_training_episodes(self.source)
                if self.source == cfg.SOURCE
                else load_episodes(self.source)
            )
            self._sample_weights = self._build_sample_weights(self._dataset)

        # ----- 一局内可变状态（reset 清空） -----
        self._rng = np.random.default_rng(seed)
        self.cols = self.rows = 0  # 当前页实际画布，≤ max_cols/rows
        self._queue: list[dict[str, Any]] = []  # 待放卡队列（顺序固定）
        self._placed: list[dict[str, Any]] = []  # 已放卡几何
        self._occ = np.zeros((self.max_rows, self.max_cols), dtype=np.int8)
        self._cursor = 0  # 下一张要放的队列下标
        self._invalid_streak = 0
        self._episode_id = ""
        self._total_cards = 0
        # synth 常无完整专家尺寸；终局空白目标现已默认填满，此字段多作兼容
        self._expert_blank_ratio: Optional[float] = None

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        """开始新一局：清棋盘，加载一条 episode，返回首观测。

        options 优先级:
            episode      — 直接用给定 dict（评估常用）
            episode_id   — 从 dataset 按 id 查找
            否则          — source==random 生成，或加权采样 dataset
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
        elif self.source == "random":
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
        """执行一步：decode (w,h) → 锚点落子 → 算奖励 → 返回五元组。

        这是 SB3 collect_rollouts 实际调用的入口。
        非法动作不改棋盘，仍针对同一张卡；合法则 cursor+1。
        """
        card = self._current()
        info: dict[str, Any] = {
            "episode_id": self._episode_id,
            "invalid": False,
            "success": False,
            "n_cards": self._total_cards,
        }
        # 队列已空：上一成功步应已 terminated；兜底直接结束
        if card is None:
            return self._obs(), 0.0, True, False, {**info, "success": True}

        # 1) 动作 → 尺寸；位置永远取当前左上空白格
        w, h = decode_action(int(action), self.max_card_w)
        anchor = top_left_empty_anchor(self._occ, self.cols, self.rows)
        if anchor is None:
            x, y = -1, -1
        else:
            x, y, _, _ = anchored_box(anchor[0], anchor[1], w, h)

        # 2) 合法性：越界或重叠 → invalid（掩码正常时应很少发生）
        valid = can_place(self._occ, x, y, w, h, self.cols, self.rows)
        terminated = truncated = False
        fail_reason: Optional[str] = None
        dens: Optional[float] = None

        if not valid:
            self._invalid_streak += 1
            info["invalid"] = True
            if self._invalid_streak >= self.max_invalid_streak:
                truncated = True
                fail_reason = "invalid_streak"
                info["fail_reason"] = fail_reason
        else:
            # 3) 落子并推进队列
            self._invalid_streak = 0
            place(self._occ, x, y, w, h)
            self._placed.append(
                {
                    "id": card["id"],
                    "w": w,
                    "h": h,
                    "x": x,
                    "y": y,
                    "type": card.get("type"),
                }
            )
            self._cursor += 1
            if self._cursor >= self._total_cards:
                terminated = True
                info["success"] = True
                dens = density(self._occ, self.cols, self.rows)
                info["sequence"] = to_sequence(
                    self._placed, cols=self.cols, rows=self.rows
                )
                info["placed"] = list(self._placed)
                info["density"] = dens
            elif not self.action_masks().any():
                # 还有卡，但锚点处已无任何合法尺寸
                truncated = True
                fail_reason = "no_legal_moves"
                info["fail_reason"] = fail_reason
                info["placed"] = list(self._placed)

        # 4) 奖励在棋盘更新之后算（occupancy / remaining 已是「放完本步」的状态）
        reward, details = compute_reward(
            {
                "valid": valid,
                "terminated": terminated,
                "truncated": truncated,
                "fail_reason": fail_reason,
                "card": card,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "placed": list(self._placed),
                "remaining": self._queue[self._cursor :],
                "cols": self.cols,
                "rows": self.rows,
                "cursor": self._cursor,
                "total_cards": self._total_cards,
                "occupancy": self._occ,
                "density": dens,
                "expert_blank_ratio": self._expert_blank_ratio,
            }
        )
        info["reward_components"] = details
        info["action_mask"] = self.action_masks()
        return self._obs(), float(reward), terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """MaskablePPO / ActionMasker 用的合法动作 bool 向量。

        True = 该 (w,h) 能从当前左上锚点放下。全 False → 无路可走。
        第一张为 textCard 时强制通栏且高度限 1～2 格。
        长宽比超过 ``MAX_ASPECT_RATIO`` 的细长条直接禁止（通栏/通高除外）。
        硬约束：每张剩余卡至少留 1 格。软约束：剩余空格不少于剩余卡
        目标面积份额的 ``AREA_RESERVE_RATIO``；若软约束会把动作全屏蔽，回退到硬约束。
        """
        current = self._current()
        if current is None:
            return np.zeros(
                cfg.action_space_size(self.max_card_w, self.max_card_h),
                dtype=bool,
            )
        mask = action_masks(
            self._occ,
            self.cols,
            self.rows,
            self.max_card_w,
            self.max_card_h,
        )
        free_before = int(
            self.cols * self.rows - self._occ[: self.rows, : self.cols].sum()
        )
        remaining_after = max(0, self._total_cards - self._cursor - 1)
        first_text = (
            self._cursor == 0
            and str(current.get("type") or "") == "textCard"
        )
        max_ratio = float(getattr(cfg, "MAX_ASPECT_RATIO", 3.0))
        reserve_ratio = float(getattr(cfg, "AREA_RESERVE_RATIO", 0.7))
        page = float(max(1, self.cols * self.rows))
        mins = [
            type_min_area(str(card.get("type") or "")) or 1
            for card in self._queue
        ]
        seq_area = max(1, sum(mins))
        remain_mins = sum(mins[self._cursor + 1 :]) if remaining_after else 0
        deserve = page * remain_mins / float(seq_area)
        reserve_cells = max(
            remaining_after,
            int(np.ceil(reserve_ratio * deserve)),
        )
        hard = mask.copy()
        for action in np.flatnonzero(mask):
            width, height = decode_action(int(action), self.max_card_w)
            if first_text and (width != self.cols or height > 2):
                hard[int(action)] = False
                continue
            if not aspect_ratio_ok(
                width, height, self.cols, self.rows, max_ratio
            ):
                hard[int(action)] = False
                continue
            if free_before - width * height < remaining_after:
                hard[int(action)] = False
        soft = hard.copy()
        if remaining_after:
            for action in np.flatnonzero(soft):
                width, height = decode_action(int(action), self.max_card_w)
                if free_before - width * height < reserve_cells:
                    soft[int(action)] = False
        return soft if soft.any() else hard

    def get_layout_sequence(self) -> str:
        """已放置卡的可渲染序列（含 grid:CxR 与 type）。"""
        return to_sequence(self._placed, cols=self.cols, rows=self.rows)

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

    # ------------------------------------------------------------------
    # 内部：观测 / 队列 / 采样 / 加载
    # ------------------------------------------------------------------

    def _obs(self) -> dict[str, np.ndarray]:
        """拼装 Dict 观测；具体通道定义在 layout.build_obs。"""
        return build_obs(
            occ=self._occ,
            queue=self._queue,
            placed=self._placed,
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
        """训练 reset 时的采样概率：难例 × 稀有棋盘 × 同型异布局 × 易堵死页。

        稀有度用 1/sqrt(count) 并封顶，避免极稀有网格权重大过头。
        """
        from collections import Counter

        from .data import has_same_type_varied_layout

        n_eps = max(1, len(episodes))
        size_counts: Counter[tuple[int, int]] = Counter()
        if self.rare_grid_weight:
            for ep in episodes:
                grid = ep.get("grid") or {}
                size_counts[(int(grid.get("cols") or 0), int(grid.get("rows") or 0))] += 1

        weights = np.ones(len(episodes), dtype=np.float64)
        for i, ep in enumerate(episodes):
            n = int(ep.get("n_cards", len(ep.get("card_queue", []))))
            ep_id = str(ep.get("id", ""))
            hard_name = any(tag in ep_id for tag in ("tablet", "phone"))
            if n >= self.hard_min_cards or hard_name:
                weights[i] *= self.hard_weight
            if self.rare_grid_weight:
                grid = ep.get("grid") or {}
                size = (int(grid.get("cols") or 0), int(grid.get("rows") or 0))
                count = max(1, size_counts.get(size, 1))
                if self.rare_grid_sqrt:
                    rare = float(np.sqrt(n_eps / float(count)))
                else:
                    rare = n_eps / float(count)
                weights[i] *= min(self.rare_grid_cap, rare)
            if has_same_type_varied_layout(ep):
                weights[i] *= self.same_type_varied_weight
            if ep_id in self.no_legal_ids:
                weights[i] *= self.no_legal_weight
            if ep_id in self.hard_size_ids:
                weights[i] *= self.hard_size_weight
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
        """从 episode dict 初始化画布尺寸与卡片队列（不改占用矩阵）。"""
        validate_episode(ep)
        self.cols = int(ep["grid"]["cols"])
        self.rows = int(ep["grid"]["rows"])
        self._queue = cards_from_episode(ep)
        self._episode_id = str(ep.get("id", "dataset"))
        self._total_cards = len(self._queue)
        self._update_expert_blank_ratio()

    def _load_random(self) -> None:
        """在线抽样一局锚点可放完的类型队列（无专家坐标）。"""
        from .tools.gen_random_grids import sample_episode

        import random as _random

        rng = _random.Random(int(self._rng.integers(0, 1_000_000_000)))
        episode = None
        for _ in range(80):
            episode = sample_episode(rng, int(self._rng.integers(1, 100_000)))
            if episode is not None:
                break
        if episode is None:
            episode = {
                "id": "random-fallback",
                "schema_version": 3,
                "grid": {"cols": 4, "rows": 4},
                "card_queue": [
                    {"id": "c0", "type": "textCard"},
                    {"id": "c1", "type": "targetStatCard"},
                    {"id": "c2", "type": "targetStatCard"},
                ],
                "expert_cards": [],
            }
        self._load_episode(episode)

    def _update_expert_blank_ratio(self) -> None:
        """若队列带齐 expert_w/h，算专家页空白率；缺任一尺寸则置 None。"""
        sizes = [
            (card.get("expert_w"), card.get("expert_h"))
            for card in self._queue
        ]
        if any(w is None or h is None for w, h in sizes):
            self._expert_blank_ratio = None
            return
        canvas_area = max(1, self.cols * self.rows)
        expert_area = sum(int(w) * int(h) for w, h in sizes)
        expert_fill = max(0.0, min(1.0, expert_area / float(canvas_area)))
        self._expert_blank_ratio = 1.0 - expert_fill
