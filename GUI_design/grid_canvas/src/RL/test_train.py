"""训练数据隔离与验证选模测试。"""

from __future__ import annotations

import unittest

from .train import _has_complete_expert_layouts, _validation_quality_key


class TestValidationSelection(unittest.TestCase):
    def test_detects_complete_expert_layouts(self):
        complete = [
            {
                "card_queue": [{"id": "c0"}, {"id": "c1"}],
                "expert_cards": [{"id": "c0"}, {"id": "c1"}],
            }
        ]
        incomplete = [
            {
                "card_queue": [{"id": "c0"}, {"id": "c1"}],
                "expert_cards": [{"id": "c0"}],
            }
        ]
        self.assertTrue(_has_complete_expert_layouts(complete))
        self.assertFalse(_has_complete_expert_layouts(incomplete))
        self.assertFalse(_has_complete_expert_layouts([]))

    def test_selection_prefers_lower_area_error_then_row_band(self):
        base = {
            "mean_area_share_error": 0.4,
            "mean_row_band_rate": 0.5,
            "mean_blank_rate": 0.1,
            "mean_ones_count": 2.0,
            "mean_reward": 5.0,
        }
        better_area = {**base, "mean_area_share_error": 0.2, "mean_reward": -10.0}
        better_row = {**base, "mean_row_band_rate": 0.8}
        worse_blank = {**base, "mean_blank_rate": 0.3}
        fewer_ones = {**base, "mean_ones_count": 0.0}

        key = _validation_quality_key(base, has_experts=False)
        self.assertGreater(
            _validation_quality_key(better_area, has_experts=False),
            key,
        )
        self.assertGreater(
            _validation_quality_key(better_row, has_experts=False),
            key,
        )
        self.assertLess(
            _validation_quality_key(worse_blank, has_experts=False),
            key,
        )
        self.assertGreater(
            _validation_quality_key(fewer_ones, has_experts=False),
            key,
        )


if __name__ == "__main__":
    unittest.main()
