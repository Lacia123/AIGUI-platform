"""奖励公式与几何边界回归测试。"""

from __future__ import annotations

import unittest

import numpy as np

from .layout import (
    exact_expert_packable,
    greedy_expert_packable,
    remaining_expert_packable,
)
from .reward import (
    BAND_WIDTH_WEIGHT,
    IMITATION_WEIGHT,
    PACKABILITY_AREA_WEIGHT,
    PACKABILITY_PENALTY,
    REWARD_TERMS,
    adjacent_placement_score,
    annotation_iou_score,
    annotation_wh_iou_score,
    annotation_wh_error,
    annotation_xy_error,
    imitation_exp_from_error,
    imitation_reward,
    logic_reward,
    packability_reward,
    min_size_reward,
    area_share_reward,
    page_structure_reward,
    page_structure_stats,
    structure_reward,
    terminal_reward,
)


def _expert(x: int = 0, y: int = 0, w: int = 1, h: int = 1) -> dict:
    return {
        "id": "c0",
        "type": "textCard",
        "expert_x": x,
        "expert_y": y,
        "expert_w": w,
        "expert_h": h,
    }


class TestExpertComparison(unittest.TestCase):
    def test_packability_is_not_an_active_reward(self) -> None:
        self.assertNotIn(packability_reward, REWARD_TERMS)

    def test_position_error_ignores_fixed_axis(self) -> None:
        card = _expert()
        self.assertEqual(annotation_xy_error(0, 2, card, 1, 3), 1.0)

    def test_position_axes_have_equal_weight(self) -> None:
        card = _expert()
        self.assertEqual(annotation_xy_error(4, 0, card, 5, 3), 0.5)
        self.assertEqual(annotation_xy_error(0, 2, card, 5, 3), 0.5)
        self.assertEqual(annotation_xy_error(4, 2, card, 5, 3), 1.0)

    def test_size_error_ignores_fixed_axis(self) -> None:
        card = _expert()
        self.assertEqual(annotation_wh_error(1, 3, card, 1, 3), 1.0)

    def test_iou_known_values(self) -> None:
        card = _expert(w=2, h=2)
        self.assertEqual(annotation_iou_score(0, 0, 2, 2, card), 1.0)
        self.assertAlmostEqual(
            annotation_iou_score(1, 0, 2, 2, card), 1.0 / 3.0
        )
        self.assertEqual(annotation_iou_score(2, 0, 2, 2, card), 0.0)

    def test_exponential_endpoints_and_monotonicity(self) -> None:
        values = [imitation_exp_from_error(x / 10) for x in range(11)]
        self.assertAlmostEqual(values[0], 1.0)
        self.assertAlmostEqual(values[-1], 0.0)
        self.assertTrue(all(a > b for a, b in zip(values, values[1:])))

    def test_imitation_has_fixed_episode_budget(self) -> None:
        card = _expert()
        base = {
            "valid": True,
            "card": card,
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 1,
            "cols": 5,
            "rows": 3,
        }
        one, _ = imitation_reward({**base, "total_cards": 1})
        ten, _ = imitation_reward({**base, "total_cards": 10})
        self.assertEqual(one, IMITATION_WEIGHT)
        self.assertEqual(ten, IMITATION_WEIGHT / 10)

    def test_imitation_ignores_position_and_rewards_exact_size(self) -> None:
        card = _expert(x=0, y=0, w=2, h=1)
        hit, hit_d = imitation_reward(
            {
                "valid": True,
                "card": card,
                "x": 0,
                "y": 0,
                "w": 2,
                "h": 1,
                "cols": 5,
                "rows": 3,
                "total_cards": 4,
            }
        )
        miss, miss_d = imitation_reward(
            {
                "valid": True,
                "card": card,
                "x": 1,
                "y": 0,
                "w": 2,
                "h": 1,
                "cols": 5,
                "rows": 3,
                "total_cards": 4,
            }
        )
        self.assertEqual(hit_d["annotation_hit"], 1.0)
        self.assertEqual(hit_d["annotation_miss"], 0.0)
        self.assertEqual(hit, IMITATION_WEIGHT / 4)
        self.assertEqual(miss_d["annotation_hit"], 1.0)
        self.assertEqual(miss_d["annotation_miss"], 0.0)
        self.assertEqual(miss, hit)

    def test_imitation_size_far_miss_worse_than_near_miss(self) -> None:
        card = _expert(x=0, y=0, w=2, h=1)
        near, _ = imitation_reward(
            {
                "valid": True,
                "card": card,
                "x": 4,
                "y": 0,
                "w": 3,
                "h": 1,
                "cols": 5,
                "rows": 3,
                "total_cards": 4,
            }
        )
        far, _ = imitation_reward(
            {
                "valid": True,
                "card": card,
                "x": 0,
                "y": 2,
                "w": 5,
                "h": 3,
                "cols": 5,
                "rows": 3,
                "total_cards": 4,
            }
        )
        self.assertLess(far, near)
        self.assertGreaterEqual(near, 0.0)
        self.assertGreaterEqual(far, 0.0)

    def test_dimension_iou_ignores_position(self) -> None:
        card = _expert(x=0, y=0, w=2, h=2)
        self.assertEqual(annotation_wh_iou_score(2, 2, card), 1.0)
        self.assertAlmostEqual(annotation_wh_iou_score(1, 2, card), 0.5)


class TestGeometryRewards(unittest.TestCase):
    @staticmethod
    def _adjacent(
        current: tuple[int, int, int, int],
        other: tuple[int, int, int, int],
    ) -> float:
        x, y, w, h = current
        ox, oy, ow, oh = other
        return adjacent_placement_score(
            {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "placed": [
                    {"x": ox, "y": oy, "w": ow, "h": oh},
                    {"x": x, "y": y, "w": w, "h": h},
                ],
            }
        )

    def test_adjacency_is_direction_independent(self) -> None:
        other = (2, 2, 2, 2)
        self.assertEqual(self._adjacent((4, 2, 1, 2), other), 1.0)
        self.assertEqual(self._adjacent((0, 2, 2, 2), other), 1.0)
        self.assertEqual(self._adjacent((2, 4, 2, 1), other), 1.0)
        self.assertEqual(self._adjacent((2, 0, 2, 2), other), 1.0)

    def test_corner_contact_is_not_adjacency(self) -> None:
        self.assertEqual(self._adjacent((1, 1, 1, 1), (0, 0, 1, 1)), 0.0)

    def test_adjacency_only_against_previous_card(self) -> None:
        score = adjacent_placement_score(
            {
                "x": 0,
                "y": 2,
                "w": 2,
                "h": 1,
                "placed": [
                    {"x": 0, "y": 0, "w": 2, "h": 2},
                    {"x": 2, "y": 0, "w": 1, "h": 1},
                    {"x": 0, "y": 2, "w": 2, "h": 1},
                ],
            }
        )
        self.assertEqual(score, 0.0)
        score_prev = adjacent_placement_score(
            {
                "x": 2,
                "y": 1,
                "w": 1,
                "h": 1,
                "placed": [
                    {"x": 0, "y": 0, "w": 2, "h": 2},
                    {"x": 2, "y": 0, "w": 1, "h": 1},
                    {"x": 2, "y": 1, "w": 1, "h": 1},
                ],
            }
        )
        self.assertEqual(score_prev, 1.0)

    def test_exact_packability_fixes_greedy_false_negative(self) -> None:
        occ = np.zeros((3, 4), dtype=np.int8)
        occ[0, 0] = 1
        remaining = [
            {"expert_w": 1, "expert_h": 3},
            {"expert_w": 3, "expert_h": 1},
        ]
        self.assertFalse(greedy_expert_packable(occ, remaining, 4, 3))
        self.assertTrue(exact_expert_packable(occ, remaining, 4, 3))
        self.assertTrue(remaining_expert_packable(occ, remaining, 4, 3))

    def test_packability_penalty_matches_miss_scale(self) -> None:
        occ = np.zeros((2, 2), dtype=np.int8)
        remaining = [{"type": "showcaseCard"}]
        reward, details = packability_reward(
            {
                "valid": True,
                "remaining": remaining,
                "occupancy": occ,
                "cols": 2,
                "rows": 2,
                "total_cards": 4,
            }
        )
        self.assertEqual(details["packability_ok"], 0.0)
        self.assertLess(reward, PACKABILITY_PENALTY * 1 / 4)

    def test_packability_scales_with_remaining_cards(self) -> None:
        occ = np.ones((2, 2), dtype=np.int8)
        one = packability_reward(
            {
                "valid": True,
                "remaining": [{"type": "Topology"}],
                "occupancy": occ,
                "cols": 2,
                "rows": 2,
                "total_cards": 4,
            }
        )[0]
        three = packability_reward(
            {
                "valid": True,
                "remaining": [{"type": "Topology"}] * 3,
                "occupancy": occ,
                "cols": 2,
                "rows": 2,
                "total_cards": 4,
            }
        )[0]
        self.assertLess(three, one)

    def test_structure_rewards_full_width_header(self) -> None:
        reward, details = structure_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 5,
                "cols": 5,
                "placed": [{"type": "textCard", "w": 5, "h": 1, "x": 0, "y": 0}],
                "remaining": [{"type": "summaryCard"}],
            }
        )
        self.assertEqual(details["structure_band"], 1.0)
        self.assertAlmostEqual(reward, BAND_WIDTH_WEIGHT * 0.15)

    def test_structure_still_bands_opening_text_run(self) -> None:
        reward, details = structure_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 1,
                "cols": 5,
                "placed": [{"type": "textCard", "w": 1, "h": 3, "x": 4, "y": 0}],
                "remaining": [{"type": "textCard"}, {"type": "targetStatCard"}],
            }
        )
        self.assertEqual(details["structure_band"], 0.0)
        self.assertAlmostEqual(reward, BAND_WIDTH_WEIGHT * (1 / 5 - 0.85))

    def test_structure_penalizes_narrow_opening(self) -> None:
        reward, details = structure_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 1,
                "cols": 4,
                "placed": [{"type": "textCard", "w": 1, "h": 4, "x": 3, "y": 0}],
                "remaining": [{"type": "targetStatCard"}],
            }
        )
        self.assertEqual(details["structure_band"], 0.0)
        self.assertAlmostEqual(reward, BAND_WIDTH_WEIGHT * (0.25 - 0.85))

    def test_structure_rewards_stacked_same_type_bands(self) -> None:
        reward, details = structure_reward(
            {
                "valid": True,
                "card": {"type": "mistakesCard"},
                "w": 4,
                "cols": 4,
                "placed": [{"type": "mistakesCard", "w": 4, "h": 2, "x": 0, "y": 0}],
                "remaining": [{"type": "mistakesCard"}, {"type": "mistakesCard"}],
            }
        )
        self.assertEqual(details["structure_band"], 1.0)
        self.assertAlmostEqual(reward, BAND_WIDTH_WEIGHT * 0.15)

    def test_structure_skips_gallery_tiles(self) -> None:
        remaining = [{"type": "showcaseCard"}] * 8
        reward, _ = structure_reward(
            {
                "valid": True,
                "card": {"type": "showcaseCard"},
                "w": 1,
                "cols": 3,
                "placed": [{"type": "showcaseCard", "w": 1, "h": 1, "x": 2, "y": 0}],
                "remaining": remaining,
            }
        )
        self.assertEqual(reward, 0.0)

    def test_structure_penalizes_fat_text_header(self) -> None:
        tall, tall_d = structure_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 3,
                "cols": 8,
                "rows": 5,
                "placed": [{"type": "textCard", "w": 8, "h": 3, "x": 0, "y": 0}],
                "remaining": [{"type": "showcaseCard"}],
            }
        )
        flat, _ = structure_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 1,
                "cols": 8,
                "rows": 5,
                "placed": [{"type": "textCard", "w": 8, "h": 1, "x": 0, "y": 0}],
                "remaining": [{"type": "showcaseCard"}],
            }
        )
        self.assertEqual(tall_d["structure_band"], 1.0)
        self.assertLess(tall, flat)

    def test_min_size_penalizes_area_below_default(self) -> None:
        reward, details = min_size_reward(
            {"valid": True, "card": {"type": "showcaseCard"}, "w": 1, "h": 1}
        )
        self.assertEqual(details["min_size_ok"], 0.0)
        self.assertAlmostEqual(reward, -8.0 * 7 / 9)

    def test_min_size_is_neutral_once_default_is_met(self) -> None:
        reward, details = min_size_reward(
            {"valid": True, "card": {"type": "targetStatCard"}, "w": 1, "h": 2}
        )
        self.assertEqual(details["min_size_ok"], 1.0)
        self.assertEqual(reward, 0.0)

    def test_min_size_keeps_tall_tendency_when_enlarged(self) -> None:
        reward, details = min_size_reward(
            {
                "valid": True,
                "card": {"type": "targetStatCard"},
                "w": 1,
                "h": 3,
                "cols": 8,
                "rows": 5,
            }
        )
        self.assertEqual(details["min_size_ok"], 1.0)
        self.assertGreater(reward, -1.0)
        self.assertLessEqual(reward, 0.0)

    def test_min_size_penalizes_tall_header_expansion(self) -> None:
        flat, _ = min_size_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 1,
                "cols": 8,
                "rows": 5,
            }
        )
        tall, _ = min_size_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 3,
                "cols": 8,
                "rows": 5,
            }
        )
        self.assertLess(tall, flat)

    def test_min_size_penalizes_flipped_tendency(self) -> None:
        reward, details = min_size_reward(
            {"valid": True, "card": {"type": "targetStatCard"}, "w": 2, "h": 1}
        )
        self.assertEqual(details["min_size_ok"], 0.0)
        self.assertLessEqual(reward, -8.0)

    def test_min_size_accepts_reshaped_area(self) -> None:
        reward, details = min_size_reward(
            {"valid": True, "card": {"type": "showcaseCard"}, "w": 4, "h": 2}
        )
        self.assertEqual(details["min_size_ok"], 1.0)
        self.assertEqual(reward, 0.0)

    def test_area_share_penalizes_below_queue_quota(self) -> None:
        reward, details = area_share_reward(
            {
                "valid": True,
                "card": {"type": "showcaseCard"},
                "w": 4,
                "h": 1,
                "cols": 8,
                "rows": 5,
                "placed": [
                    {"type": "textCard"},
                    {"type": "showcaseCard"},
                    {"type": "Topology"},
                    {"type": "targetStatCard"},
                    {"type": "mistakesCard"},
                    {"type": "mistakesCard"},
                    {"type": "mistakesCard"},
                ],
                "remaining": [],
            }
        )
        self.assertAlmostEqual(details["area_share_target"], 18.0)
        self.assertLess(reward, 0.0)

    def test_area_share_rewards_meeting_quota(self) -> None:
        short, _ = area_share_reward(
            {
                "valid": True,
                "card": {"type": "contentSummaryCard"},
                "w": 2,
                "h": 2,
                "cols": 4,
                "rows": 4,
                "placed": [
                    {"type": "contentSummaryCard"},
                    {"type": "contentSummaryCard"},
                ],
                "remaining": [],
            }
        )
        full, details = area_share_reward(
            {
                "valid": True,
                "card": {"type": "contentSummaryCard"},
                "w": 4,
                "h": 2,
                "cols": 4,
                "rows": 4,
                "placed": [
                    {"type": "contentSummaryCard"},
                    {"type": "contentSummaryCard"},
                ],
                "remaining": [],
            }
        )
        self.assertAlmostEqual(details["area_share_target"], 8.0)
        self.assertAlmostEqual(full, 0.0)
        self.assertLess(short, full)

    def test_area_share_penalizes_oversized_card(self) -> None:
        reward, details = area_share_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 1,
                "cols": 8,
                "rows": 5,
                "placed": [
                    {"type": "textCard"},
                    {"type": "showcaseCard"},
                    {"type": "Topology"},
                    {"type": "targetStatCard"},
                    {"type": "mistakesCard"},
                    {"type": "mistakesCard"},
                    {"type": "mistakesCard"},
                ],
                "remaining": [],
            }
        )
        self.assertAlmostEqual(details["area_share_target"], 4.0)
        self.assertEqual(details["area_share_ok"], 0.0)
        self.assertLess(reward, 0.0)

    def test_area_share_penalizes_far_overshoot(self) -> None:
        slim, _ = area_share_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 1,
                "cols": 8,
                "rows": 5,
                "placed": [{"type": "textCard"}, {"type": "showcaseCard"}],
                "remaining": [],
            }
        )
        fat, details = area_share_reward(
            {
                "valid": True,
                "card": {"type": "textCard"},
                "w": 8,
                "h": 3,
                "cols": 8,
                "rows": 5,
                "placed": [{"type": "textCard"}, {"type": "showcaseCard"}],
                "remaining": [],
            }
        )
        self.assertLess(fat, slim)
        self.assertEqual(details["area_share_ok"], 0.0)

    def test_area_share_only_compares_page_area(self) -> None:
        base = {
            "valid": True,
            "card": {"type": "targetStatCard"},
            "cols": 4,
            "rows": 4,
            "placed": [
                {"type": "targetStatCard"},
                {"type": "targetStatCard"},
            ],
            "remaining": [],
            "total_cards": 2,
        }
        wide, _ = area_share_reward({**base, "w": 4, "h": 2})
        tall, _ = area_share_reward({**base, "w": 2, "h": 4})
        self.assertEqual(wide, tall)

    def test_page_structure_is_an_active_reward(self) -> None:
        self.assertIn(page_structure_reward, REWARD_TERMS)

    def test_page_structure_is_zero_until_terminal(self) -> None:
        placed = [
            {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
            {"type": "targetStatCard", "x": 0, "y": 1, "w": 2, "h": 3},
            {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 3},
        ]
        reward, details = page_structure_reward(
            {
                "valid": True,
                "terminated": False,
                "truncated": False,
                "placed": placed,
                "cols": 4,
                "rows": 4,
            }
        )
        self.assertEqual(reward, 0.0)
        self.assertEqual(details["row_band_rate"], 1.0)

    def test_page_structure_rewards_complete_row_bands(self) -> None:
        placed = [
            {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
            {"type": "targetStatCard", "x": 0, "y": 1, "w": 2, "h": 3},
            {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 3},
        ]
        reward, details = page_structure_reward(
            {
                "terminated": True,
                "placed": placed,
                "cols": 4,
                "rows": 4,
            }
        )
        self.assertEqual(details["row_band_rate"], 1.0)
        self.assertEqual(details["split_reuse"], 1.0)
        self.assertGreater(reward, 15.0)

    def test_page_structure_penalizes_l_shape(self) -> None:
        clean = page_structure_stats(
            [
                {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                {"type": "targetStatCard", "x": 0, "y": 1, "w": 2, "h": 3},
                {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 3},
            ],
            4,
            4,
        )
        messy = page_structure_stats(
            [
                {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                {"type": "targetStatCard", "x": 0, "y": 1, "w": 3, "h": 1},
                {"type": "targetStatCard", "x": 3, "y": 1, "w": 1, "h": 3},
                {"type": "showcaseCard", "x": 0, "y": 2, "w": 3, "h": 1},
                {"type": "mistakesCard", "x": 0, "y": 3, "w": 3, "h": 1},
            ],
            4,
            4,
        )
        self.assertGreater(clean["row_band_rate"], messy["row_band_rate"])

    def test_page_structure_full_width_stack_reuses_no_splits(self) -> None:
        header_split = page_structure_stats(
            [
                {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                {"type": "targetStatCard", "x": 0, "y": 1, "w": 2, "h": 3},
                {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 3},
            ],
            4,
            4,
        )
        banner_stack = page_structure_stats(
            [
                {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                {"type": "showcaseCard", "x": 0, "y": 1, "w": 4, "h": 1},
                {"type": "targetStatCard", "x": 0, "y": 2, "w": 4, "h": 1},
                {"type": "targetStatCard", "x": 0, "y": 3, "w": 4, "h": 1},
            ],
            4,
            4,
        )
        self.assertGreater(header_split["row_band_rate"], banner_stack["row_band_rate"])
        self.assertGreater(header_split["nested_split"], banner_stack["nested_split"])
        self.assertGreater(banner_stack["thin_banner_rate"], 0.5)
        self.assertEqual(banner_stack["split_reuse"], 0.0)

    def test_page_structure_rewards_handcrafted_sidebar_nesting(self) -> None:
        """手工页 2：标题 + 侧栏 showcase + 指标行 + 两块内容。"""
        nested, nested_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 8, "h": 1},
                    {"type": "showcaseCard", "x": 0, "y": 1, "w": 2, "h": 4},
                    {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 1},
                    {"type": "targetStatCard", "x": 4, "y": 1, "w": 2, "h": 1},
                    {"type": "targetStatCard", "x": 6, "y": 1, "w": 2, "h": 1},
                    {"type": "Topology", "x": 2, "y": 2, "w": 3, "h": 3},
                    {"type": "contentSummaryCard", "x": 5, "y": 2, "w": 3, "h": 3},
                ],
                "cols": 8,
                "rows": 5,
            }
        )
        banners, banners_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 8, "h": 1},
                    {"type": "showcaseCard", "x": 0, "y": 1, "w": 8, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 2, "w": 8, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 3, "w": 2, "h": 2},
                    {"type": "targetStatCard", "x": 2, "y": 3, "w": 2, "h": 2},
                    {"type": "Topology", "x": 4, "y": 3, "w": 1, "h": 2},
                    {"type": "contentSummaryCard", "x": 5, "y": 3, "w": 3, "h": 2},
                ],
                "cols": 8,
                "rows": 5,
            }
        )
        self.assertGreaterEqual(nested_d["nested_split"], 0.99)
        self.assertGreater(nested_d["type_split"], banners_d["type_split"])
        self.assertGreater(nested, banners)

    def test_page_structure_penalizes_non_header_banners(self) -> None:
        stacked, stacked_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                    {"type": "showcaseCard", "x": 0, "y": 1, "w": 4, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 2, "w": 4, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 3, "w": 4, "h": 1},
                ],
                "cols": 4,
                "rows": 4,
            }
        )
        split, split_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 4, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 1, "w": 2, "h": 3},
                    {"type": "targetStatCard", "x": 2, "y": 1, "w": 2, "h": 3},
                ],
                "cols": 4,
                "rows": 4,
            }
        )
        self.assertGreater(split, stacked)
        self.assertGreater(stacked_d["thin_banner_rate"], split_d["thin_banner_rate"])
        self.assertGreaterEqual(split_d["type_split"], stacked_d["type_split"])

    def test_page_structure_same_type_stack_does_not_need_sidebar(self) -> None:
        reward, details = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "mistakesCard", "x": 0, "y": 0, "w": 4, "h": 2},
                    {"type": "mistakesCard", "x": 0, "y": 2, "w": 4, "h": 2},
                    {"type": "mistakesCard", "x": 0, "y": 4, "w": 4, "h": 2},
                ],
                "cols": 4,
                "rows": 6,
            }
        )
        self.assertNotIn("branch_sidebar", details)
        self.assertGreater(details["branch_mist_cluster"], 0.9)
        self.assertGreater(reward, 12.0)

    def test_page_structure_header_branch_only_if_first_card_is_text(self) -> None:
        _, details = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "__rawMarkdown__", "x": 0, "y": 0, "w": 4, "h": 3},
                    {"type": "textCard", "x": 0, "y": 3, "w": 4, "h": 3},
                ],
                "cols": 4,
                "rows": 6,
            }
        )
        self.assertNotIn("branch_header", details)

    def test_page_structure_fill_cards_should_grow_on_wide_pages(self) -> None:
        grown, grown_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 8, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 1, "w": 4, "h": 2},
                    {"type": "targetStatCard", "x": 4, "y": 1, "w": 4, "h": 2},
                    {"type": "Topology", "x": 0, "y": 3, "w": 4, "h": 2},
                    {"type": "__rawMarkdown__", "x": 4, "y": 3, "w": 4, "h": 2},
                ],
                "cols": 8,
                "rows": 5,
            }
        )
        banners, banners_d = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 8, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 1, "w": 8, "h": 1},
                    {"type": "targetStatCard", "x": 0, "y": 2, "w": 8, "h": 1},
                    {"type": "Topology", "x": 0, "y": 3, "w": 8, "h": 1},
                    {"type": "__rawMarkdown__", "x": 0, "y": 4, "w": 8, "h": 1},
                ],
                "cols": 8,
                "rows": 5,
            }
        )
        self.assertGreater(grown_d["branch_fill_shape"], banners_d["branch_fill_shape"])
        self.assertGreater(grown_d["branch_not_all_banners"], banners_d["branch_not_all_banners"])
        self.assertGreater(grown, banners)

    def test_page_structure_few_cards_prefer_growing_not_banners(self) -> None:
        grown, _ = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "[table:commonStyle]", "x": 0, "y": 0, "w": 3, "h": 2},
                    {"type": "__rawMarkdown__", "x": 0, "y": 2, "w": 3, "h": 4},
                ],
                "cols": 3,
                "rows": 6,
            }
        )
        left_blank, _ = page_structure_reward(
            {
                "terminated": True,
                "placed": [
                    {"type": "[table:commonStyle]", "x": 0, "y": 0, "w": 2, "h": 2},
                    {"type": "__rawMarkdown__", "x": 2, "y": 0, "w": 1, "h": 2},
                ],
                "cols": 3,
                "rows": 6,
            }
        )
        self.assertGreater(grown, left_blank)

    def test_packability_area_overflow_is_dense(self) -> None:
        occ = np.ones((3, 4), dtype=np.int8)
        remaining = [{"type": "contentSummaryCard"}]
        reward, details = packability_reward(
            {
                "valid": True,
                "remaining": remaining,
                "occupancy": occ,
                "cols": 4,
                "rows": 3,
                "total_cards": 2,
            }
        )
        area = -PACKABILITY_AREA_WEIGHT * 4 / 12
        sequential = PACKABILITY_PENALTY * 1 / 2
        self.assertEqual(details["packability_ok"], 0.0)
        self.assertAlmostEqual(details["packability_area"], area)
        self.assertAlmostEqual(reward, sequential + area)

    def test_expert_no_longer_disables_generic_logic(self) -> None:
        card = _expert(w=2, h=1)
        _, details = logic_reward(
            {
                "valid": True,
                "card": card,
                "x": 0,
                "y": 0,
                "w": 2,
                "h": 1,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 2, "h": 1},
                ],
            }
        )
        self.assertGreater(details["logic_origin"], 0.0)

    def test_no_expert_still_allows_logic(self) -> None:
        card = {"id": "c0", "type": "textCard"}
        _, details = logic_reward(
            {
                "valid": True,
                "card": card,
                "x": 0,
                "y": 0,
                "w": 1,
                "h": 1,
                "placed": [
                    {"type": "textCard", "x": 0, "y": 0, "w": 1, "h": 1},
                ],
            }
        )
        self.assertGreater(details["logic_origin"], 0.0)


class TestTerminalReward(unittest.TestCase):
    def test_expert_blank_ratio_is_ignored(self) -> None:
        _, details = terminal_reward(
            {
                "terminated": True,
                "truncated": False,
                "density": 0.4,
                "expert_blank_ratio": 0.6,
                "cursor": 1,
                "total_cards": 1,
                "cols": 5,
                "rows": 3,
            }
        )
        self.assertAlmostEqual(details["blank_error"], 0.6)
        self.assertAlmostEqual(details["terminal"], -16.0 * 0.6)

    def test_full_page_has_zero_terminal_score(self) -> None:
        reward, details = terminal_reward(
            {
                "terminated": True,
                "truncated": False,
                "density": 1.0,
                "cursor": 2,
                "total_cards": 2,
                "cols": 2,
                "rows": 2,
            }
        )
        self.assertEqual(details["terminal_full_bonus"], 0.0)
        self.assertEqual(reward, 0.0)


if __name__ == "__main__":
    unittest.main()
