"""Beam Search 与整页结构统计的回归。"""

from __future__ import annotations

import unittest

from .env import LayoutEnv
from .search import beam_search


class TestBeamSearch(unittest.TestCase):
    def test_beam_fills_a_small_page(self) -> None:
        episode = {
            "id": "beam-small",
            "schema_version": 3,
            "grid": {"cols": 4, "rows": 4},
            "card_queue": [
                {"id": "c0", "type": "textCard"},
                {"id": "c1", "type": "targetStatCard"},
                {"id": "c2", "type": "targetStatCard"},
            ],
            "expert_cards": [],
        }
        env = LayoutEnv(source="synth", episodes=[episode], seed=0)
        result = beam_search(env, episode, beam_width=6)
        self.assertTrue(result["success"])
        self.assertLessEqual(result["blank_rate"], 1e-9)
        self.assertGreaterEqual(result["row_band_rate"], 0.99)
        self.assertEqual(len(result["actions"]), 3)


if __name__ == "__main__":
    unittest.main()
