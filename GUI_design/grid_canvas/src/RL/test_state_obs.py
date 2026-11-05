"""clean schema v3 / State / 左上锚点宽高动作测试。

用法（在 grid_canvas/src 下）:
  python -m RL.test_state_obs
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

if __package__:
    from .card_types import (
        CARD_IDX_AREA_SHARE,
        CARD_IDX_COLS,
        CARD_IDX_CONSECUTIVE_SAME,
        CARD_IDX_INDEX,
        CARD_IDX_MIN_H,
        CARD_IDX_MIN_W,
        CARD_IDX_REMAIN,
        CARD_IDX_ROWS,
        CARD_IDX_SAME_ORDINAL,
        CARD_IDX_SAME_TOTAL,
        CARD_OBS_DIM,
        LAYOUT_STATS_DIM,
        SPATIAL_CHANNELS,
        SPATIAL_ANCHOR,
        SPATIAL_FREE_DOWN,
        SPATIAL_FREE_RIGHT,
        SPATIAL_OCC,
        SPATIAL_PAGE,
    )
    from .data import audit_observation_aliasing, load_episodes
    from .env import LayoutEnv
    from .layout import (
        action_masks,
        anchored_box,
        build_obs,
        decode_action,
        encode_action,
        free_span_maps,
        place,
        top_left_empty_anchor,
    )
else:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from RL.card_types import (
        CARD_IDX_AREA_SHARE,
        CARD_IDX_COLS,
        CARD_IDX_CONSECUTIVE_SAME,
        CARD_IDX_INDEX,
        CARD_IDX_MIN_H,
        CARD_IDX_MIN_W,
        CARD_IDX_REMAIN,
        CARD_IDX_ROWS,
        CARD_IDX_SAME_ORDINAL,
        CARD_IDX_SAME_TOTAL,
        CARD_OBS_DIM,
        LAYOUT_STATS_DIM,
        SPATIAL_CHANNELS,
        SPATIAL_ANCHOR,
        SPATIAL_FREE_DOWN,
        SPATIAL_FREE_RIGHT,
        SPATIAL_OCC,
        SPATIAL_PAGE,
    )
    from RL.data import audit_observation_aliasing, load_episodes
    from RL.env import LayoutEnv
    from RL.layout import (
        action_masks,
        anchored_box,
        build_obs,
        decode_action,
        encode_action,
        free_span_maps,
        place,
        top_left_empty_anchor,
    )


def _make_queue() -> list[dict]:
    return [
        {
            "id": "c0",
            "type": "textCard",
            "psuip": "# Title\n\n- item",
            "expert_w": 2,
            "expert_h": 1,
            "expert_x": 0,
            "expert_y": 0,
        },
        {
            "id": "c1",
            "type": "summaryCard",
            "psuip": "summary",
            "expert_w": 1,
            "expert_h": 1,
            "expert_x": 2,
            "expert_y": 0,
        },
        {
            "id": "c2",
            "type": "textCard",
            "psuip": "footer text",
            "expert_w": 2,
            "expert_h": 1,
            "expert_x": 0,
            "expert_y": 1,
        },
    ]


class TestStateObs(unittest.TestCase):
    def test_env_uses_explicit_episode_subset(self):
        episodes = load_episodes("all")
        chosen = episodes[0]
        env = LayoutEnv(source="all", episodes=[chosen], seed=0)
        for seed in range(5):
            _obs, info = env.reset(seed=seed)
            self.assertEqual(info["episode_id"], chosen["id"])

    def test_env_rejects_empty_episode_subset(self):
        with self.assertRaisesRegex(ValueError, "episodes 不能为空"):
            LayoutEnv(source="all", episodes=[])

    def test_first_text_card_mask_requires_full_width_and_short_height(self):
        episodes = load_episodes("synth")
        episode = next(
            ep
            for ep in episodes
            if (ep.get("card_queue") or [{}])[0].get("type") == "textCard"
        )
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        env.reset(seed=0)
        legal = np.flatnonzero(env.action_masks())
        self.assertGreater(len(legal), 0)
        sizes = {decode_action(int(action), env.max_card_w) for action in legal}
        widths = {width for width, _height in sizes}
        heights = {height for _width, height in sizes}
        self.assertEqual(widths, {env.cols})
        self.assertTrue(heights.issubset({1, 2}))

    def test_action_mask_forbids_thin_strips(self):
        episode = {
            "id": "aspect-limit",
            "schema_version": 3,
            "grid": {"cols": 8, "rows": 5},
            "card_queue": [
                {"id": "c0", "type": "targetStatCard"},
                {"id": "c1", "type": "targetStatCard"},
            ],
            "expert_cards": [],
        }
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        env.reset(seed=0)
        sizes = {
            decode_action(int(action), env.max_card_w)
            for action in np.flatnonzero(env.action_masks())
        }
        self.assertTrue(sizes)
        self.assertNotIn((7, 1), sizes)
        self.assertNotIn((1, 4), sizes)
        self.assertTrue(any(width == height for width, height in sizes))

    def test_action_mask_reserves_remaining_area_share(self):
        episode = {
            "id": "reserve-area",
            "schema_version": 3,
            "grid": {"cols": 4, "rows": 4},
            "card_queue": [
                {"id": "c0", "type": "contentSummaryCard"},
                {"id": "c1", "type": "contentSummaryCard"},
                {"id": "c2", "type": "contentSummaryCard"},
                {"id": "c3", "type": "contentSummaryCard"},
            ],
            "expert_cards": [],
        }
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        env.reset(seed=0)
        sizes = {
            decode_action(int(action), env.max_card_w)
            for action in np.flatnonzero(env.action_masks())
        }
        self.assertTrue(sizes)
        self.assertTrue(all(width * height <= 7 for width, height in sizes))
        self.assertNotIn((4, 3), sizes)
        self.assertNotIn((4, 4), sizes)

    def test_action_mask_reserves_one_cell_per_remaining_card(self):
        episode = {
            "id": "reserve-cells",
            "schema_version": 3,
            "grid": {"cols": 2, "rows": 2},
            "card_queue": [
                {"id": "c0", "type": "Topology"},
                {"id": "c1", "type": "Topology"},
                {"id": "c2", "type": "Topology"},
            ],
            "expert_cards": [],
        }
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        env.reset(seed=0)
        sizes = {
            decode_action(int(action), env.max_card_w)
            for action in np.flatnonzero(env.action_masks())
        }
        self.assertTrue(sizes)
        self.assertTrue(all(width * height <= 2 for width, height in sizes))
        self.assertNotIn((2, 2), sizes)

    def test_first_non_text_card_keeps_multiple_widths(self):
        episodes = load_episodes("synth")
        episode = next(
            ep
            for ep in episodes
            if (ep.get("card_queue") or [{}])[0].get("type") != "textCard"
        )
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        env.reset(seed=0)
        legal = np.flatnonzero(env.action_masks())
        widths = {decode_action(int(action), env.max_card_w)[0] for action in legal}
        self.assertGreater(len(widths), 1)

    def test_all_datasets_use_clean_schema(self):
        episodes = load_episodes("all")
        self.assertGreater(len(episodes), 0)
        for ep in episodes:
            self.assertEqual(ep["schema_version"], 3)
            self.assertIn("card_queue", ep)
            self.assertIn("expert_cards", ep)
            self.assertNotIn("cards_wh", ep)
            self.assertNotIn("target_xy", ep)

    def test_env_obs_shape_and_contains(self):
        env = LayoutEnv(source="random", seed=0)
        obs, _info = env.reset(seed=0)
        self.assertEqual(obs["spatial"].shape, (SPATIAL_CHANNELS, env.max_rows, env.max_cols))
        self.assertEqual(obs["cards"].shape, (env.max_cards, CARD_OBS_DIM))
        self.assertEqual(obs["grid"].shape, (LAYOUT_STATS_DIM,))
        self.assertEqual(obs["cursor"].shape, (1,))
        self.assertGreaterEqual(float(obs["cursor"][0]), 0.0)
        self.assertLessEqual(float(obs["cursor"][0]), 1.0)
        self.assertTrue(env.observation_space.contains(obs))

    def test_free_spans(self):
        cols, rows = 4, 3
        max_c, max_r = 7, 4
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        place(occ, 0, 0, 2, 1)
        right, down = free_span_maps(occ, cols, rows, max_c, max_r)
        self.assertAlmostEqual(float(right[0, 2]), 2.0 / 7.0, places=5)
        self.assertAlmostEqual(float(down[1, 0]), 2.0 / 4.0, places=5)

    def test_free_span_origin_differs_by_canvas_width(self):
        max_c, max_r = 8, 6
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        right_5, _ = free_span_maps(occ, 5, 3, max_c, max_r)
        right_8, _ = free_span_maps(occ, 8, 5, max_c, max_r)
        self.assertAlmostEqual(float(right_5[0, 0]), 5.0 / 8.0, places=5)
        self.assertAlmostEqual(float(right_8[0, 0]), 1.0, places=5)
        self.assertGreater(float(right_8[0, 0]), float(right_5[0, 0]))

    def test_layout_stats_and_hidden_geometry(self):
        cols, rows = 4, 2
        max_c, max_r, max_cards = 7, 4, 32
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        queue = _make_queue()
        obs = build_obs(
            occ=occ,
            queue=queue,
            placed=[],
            cursor=0,
            cols=cols,
            rows=rows,
            max_cols=max_c,
            max_rows=max_r,
            max_cards=max_cards,
            total_cards=len(queue),
        )
        self.assertAlmostEqual(float(obs["grid"][2]), 1.0, places=5)
        self.assertAlmostEqual(float(obs["grid"][3]), 3.0 / max_cards, places=5)
        self.assertEqual(float(obs["grid"][4]), 0.0)
        np.testing.assert_array_equal(obs["cards"][:3, 2:6], 0.0)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_COLS]), 4.0 / max_c, places=5)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_ROWS]), 2.0 / max_r, places=5)
        self.assertAlmostEqual(float(obs["cards"][1, CARD_IDX_INDEX]), 1.0 / 3.0, places=5)
        self.assertAlmostEqual(float(obs["cards"][1, CARD_IDX_REMAIN]), 2.0 / 3.0, places=5)
        # 两张 textCard：ordinal 分别为 0.5 / 1.0（1/2, 2/2）
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_SAME_ORDINAL]), 0.5, places=5)
        self.assertAlmostEqual(float(obs["cards"][2, CARD_IDX_SAME_ORDINAL]), 1.0, places=5)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_SAME_TOTAL]), 2.0 / max_cards, places=5)
        self.assertAlmostEqual(
            float(obs["cards"][0, CARD_IDX_CONSECUTIVE_SAME]), 1.0 / max_cards
        )
        self.assertAlmostEqual(float(obs["cursor"][0]), 0.0, places=5)
        self.assertEqual(float(obs["spatial"][SPATIAL_PAGE, 0, 0]), 1.0)
        self.assertEqual(float(obs["spatial"][SPATIAL_OCC].sum()), 0.0)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_MIN_W]), 2.0 / max_c, places=5)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_MIN_H]), 1.0 / max_r, places=5)
        self.assertAlmostEqual(float(obs["cards"][0, CARD_IDX_AREA_SHARE]), 2.0 / 6.0, places=5)
        self.assertAlmostEqual(float(obs["grid"][5]), 6.0 / 8.0, places=5)

    def test_same_type_ordinal_differs(self):
        queue = _make_queue()
        obs = build_obs(
            occ=np.zeros((4, 7), dtype=np.int8),
            queue=queue,
            placed=[],
            cursor=0,
            cols=4,
            rows=2,
            max_cols=7,
            max_rows=4,
            max_cards=32,
            total_cards=3,
        )
        self.assertNotEqual(
            float(obs["cards"][0, CARD_IDX_SAME_ORDINAL]),
            float(obs["cards"][2, CARD_IDX_SAME_ORDINAL]),
        )

    def test_canvas_width_changes_first_card_token(self):
        queue = _make_queue()[:1]
        occ = np.zeros((6, 8), dtype=np.int8)
        obs5 = build_obs(
            occ=occ,
            queue=queue,
            placed=[],
            cursor=0,
            cols=5,
            rows=3,
            max_cols=8,
            max_rows=6,
            max_cards=32,
            total_cards=1,
        )
        obs8 = build_obs(
            occ=occ,
            queue=queue,
            placed=[],
            cursor=0,
            cols=8,
            rows=5,
            max_cols=8,
            max_rows=6,
            max_cards=32,
            total_cards=1,
        )
        self.assertNotEqual(
            float(obs5["cards"][0, CARD_IDX_COLS]),
            float(obs8["cards"][0, CARD_IDX_COLS]),
        )
        self.assertGreater(
            float(obs8["spatial"][SPATIAL_FREE_RIGHT, 0, 0]),
            float(obs5["spatial"][SPATIAL_FREE_RIGHT, 0, 0]),
        )

    def test_action_mask_exposes_multiple_sizes(self):
        cols, rows, max_c, max_r = 3, 2, 8, 6
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        mask = action_masks(occ, cols, rows, max_c, max_r)
        one = encode_action(1, 1, max_c)
        wide = encode_action(2, 1, max_c)
        tall = encode_action(1, 2, max_c)
        self.assertTrue(mask[one])
        self.assertTrue(mask[wide])
        self.assertTrue(mask[tall])
        self.assertEqual(mask.size, max_c * max_r)

    def test_irregular_blank_masks_each_anchored_rectangle(self):
        cols, rows, max_c, max_r = 4, 3, 8, 6
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        occ[1, 1] = 1
        self.assertEqual(top_left_empty_anchor(occ, cols, rows), (0, 0))
        mask = action_masks(occ, cols, rows, max_c, max_r)
        self.assertTrue(mask[encode_action(2, 1, max_c)])
        self.assertTrue(mask[encode_action(1, 2, max_c)])
        self.assertFalse(mask[encode_action(2, 2, max_c)])

    def test_second_card_starts_at_top_left_of_remaining(self):
        cols, rows, max_c, max_r = 5, 3, 8, 6
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        place(occ, 0, 0, 5, 1)
        self.assertEqual(top_left_empty_anchor(occ, cols, rows), (0, 1))
        mask = action_masks(occ, cols, rows, max_c, max_r)
        self.assertTrue(mask[encode_action(2, 2, max_c)])
        self.assertEqual(anchored_box(0, 1, 2, 2), (0, 1, 2, 2))

    def test_no_expert_leakage(self):
        cols, rows = 5, 3
        max_c, max_r, max_cards = 7, 4, 32
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        queue_a = _make_queue()
        queue_b = _make_queue()
        for card in queue_b:
            card["expert_x"] = 99
            card["expert_y"] = 99
            card["expert_w"] = 9
            card["expert_h"] = 9

        obs_a = build_obs(
            occ=occ,
            queue=queue_a,
            placed=[],
            cursor=0,
            cols=cols,
            rows=rows,
            max_cols=max_c,
            max_rows=max_r,
            max_cards=max_cards,
            total_cards=len(queue_a),
        )
        obs_b = build_obs(
            occ=occ,
            queue=queue_b,
            placed=[],
            cursor=0,
            cols=cols,
            rows=rows,
            max_cols=max_c,
            max_rows=max_r,
            max_cards=max_cards,
            total_cards=len(queue_b),
        )
        for key in ("spatial", "cards", "grid", "cursor"):
            np.testing.assert_array_equal(obs_a[key], obs_b[key])

    def test_free_span_channels_present(self):
        cols, rows = 3, 2
        max_c, max_r = 7, 4
        occ = np.zeros((max_r, max_c), dtype=np.int8)
        queue = _make_queue()[:1]
        obs = build_obs(
            occ=occ,
            queue=queue,
            placed=[],
            cursor=0,
            cols=cols,
            rows=rows,
            max_cols=max_c,
            max_rows=max_r,
            max_cards=32,
            total_cards=1,
        )
        self.assertEqual(obs["spatial"].shape[0], SPATIAL_CHANNELS)
        self.assertGreater(float(obs["spatial"][SPATIAL_FREE_RIGHT, 0, 0]), 0.0)
        self.assertGreater(float(obs["spatial"][SPATIAL_FREE_DOWN, 0, 0]), 0.0)
        self.assertEqual(float(obs["spatial"][SPATIAL_ANCHOR, 0, 0]), 1.0)

    def test_rare_grid_is_upweighted(self):
        env = LayoutEnv(source="all", seed=0)
        weights = env._sample_weights
        self.assertIsNotNone(weights)
        by_size: dict[tuple[int, int], list[float]] = {}
        for ep, w in zip(env._dataset, weights):
            grid = ep.get("grid") or {}
            key = (int(grid.get("cols") or 0), int(grid.get("rows") or 0))
            by_size.setdefault(key, []).append(float(w))
        if (5, 3) in by_size and (8, 5) in by_size:
            mean_5 = sum(by_size[(5, 3)]) / len(by_size[(5, 3)])
            mean_8 = sum(by_size[(8, 5)]) / len(by_size[(8, 5)])
            self.assertGreater(mean_8, mean_5)

    def test_observation_alias_audit_runs(self):
        report = audit_observation_aliasing(source="all", warn=False)
        self.assertIn("conflict_groups", report)
        self.assertGreaterEqual(report["total_episodes"], 1)


class TestPolicySmoke(unittest.TestCase):
    def test_features_extractor_forward(self):
        try:
            import torch
            from RL.policy import LayoutFeaturesExtractor
        except ImportError as exc:
            self.skipTest(f"依赖不可用: {exc}")

        env = LayoutEnv(source="random", seed=1)
        obs, _ = env.reset(seed=1)
        extractor = LayoutFeaturesExtractor(env.observation_space, features_dim=256)
        batch = {
            k: torch.as_tensor(v).unsqueeze(0)
            for k, v in obs.items()
        }
        out = extractor(batch)
        self.assertEqual(tuple(out.shape), (1, 256))
        self.assertFalse(torch.isnan(out).any().item())

    def test_cross_attention_no_nan_on_empty_page(self):
        try:
            import torch
            from RL.policy import LayoutFeaturesExtractor
        except ImportError as exc:
            self.skipTest(f"依赖不可用: {exc}")

        env = LayoutEnv(source="all", seed=0)
        episodes = load_episodes("all")
        obs, _ = env.reset(seed=0, options={"episode": episodes[0]})
        # 人为清空 page 掩码
        obs["spatial"][SPATIAL_PAGE].fill(0)
        extractor = LayoutFeaturesExtractor(env.observation_space, features_dim=256)
        batch = {k: torch.as_tensor(v).unsqueeze(0) for k, v in obs.items()}
        out = extractor(batch)
        self.assertFalse(torch.isnan(out).any().item())

    def test_fuse_lifts_scalars_and_keeps_dim(self):
        try:
            import torch
            from RL.policy import LayoutFeaturesExtractor
        except ImportError as exc:
            self.skipTest(f"依赖不可用: {exc}")

        env = LayoutEnv(source="all", seed=0)
        episodes = load_episodes("all")
        obs, _ = env.reset(seed=0, options={"episode": episodes[0]})
        extractor = LayoutFeaturesExtractor(env.observation_space, features_dim=256)
        self.assertEqual(extractor.extra_in.in_features, LAYOUT_STATS_DIM + 1)
        self.assertEqual(extractor.extra_in.out_features, extractor.d_model)
        self.assertEqual(extractor.fuse_role_emb.num_embeddings, 5)
        self.assertGreaterEqual(len(extractor.fuse_res), 1)
        batch = {k: torch.as_tensor(v).unsqueeze(0) for k, v in obs.items()}
        out = extractor(batch)
        self.assertEqual(tuple(out.shape), (1, 256))
        self.assertFalse(torch.isnan(out).any().item())
        out.sum().backward()
        extra_grad = extractor.extra_in.weight.grad
        self.assertIsNotNone(extra_grad)
        self.assertGreater(float(extra_grad.abs().sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
