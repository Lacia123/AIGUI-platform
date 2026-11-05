import unittest

from tools_layout.candidates import generate_candidates
from tools_layout.domain import (
    Canvas,
    CardNode,
    ContainerNode,
    canonical_key,
    leaf_indices,
    node_from_dict,
    render_psuip,
)
from tools_layout.evaluation import uncoverable_reason
from tools_layout.geometry import layout_geometry, min_size, tree_to_grid_sequence
from tools_layout.parser import parse_cards
from tools_layout.pipeline import candidates_to_dict, rank_layouts
from tools_layout.scoring import score_tree


SOURCE = """\
<heroCard>
  <title>课程总览</title>
</heroCard>
<targetStatCard><value>80%</value></targetStatCard>
<targetStatCard><value>90%</value></targetStatCard>
<textCard><p>下一步学习内容</p></textCard>
"""


class ParserTest(unittest.TestCase):
    def test_parses_top_level_cards_and_preserves_source(self) -> None:
        cards = parse_cards(SOURCE)
        self.assertEqual(
            [card.card_type for card in cards],
            ["heroCard", "targetStatCard", "targetStatCard", "textCard"],
        )
        self.assertIn("<title>课程总览</title>", cards[0].psuip)
        self.assertGreater(cards[0].char_count, 0)


class CandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cards = parse_cards(SOURCE)
        self.canvas = Canvas(1024, 768)

    def test_candidates_keep_every_card_in_order(self) -> None:
        candidates = generate_candidates(
            self.cards, self.canvas, beam_width=64, max_depth=4
        )
        self.assertGreater(len(candidates), 2)
        for tree in candidates:
            self.assertEqual(leaf_indices(tree), [0, 1, 2, 3])

    def test_scoring_is_explainable(self) -> None:
        tree = ContainerNode(
            "column",
            tuple(
                # A flat column is always a legal baseline.
                candidate
                for candidate in generate_candidates(
                    self.cards, self.canvas, beam_width=8
                )[0].children
            ),
        )
        score, penalties = score_tree(tree, self.cards, self.canvas)
        self.assertAlmostEqual(score, sum(penalties.values()))
        self.assertIn("overflow", penalties)
        self.assertIn("complexity", penalties)

    def test_hand_sidebar_tree_is_generated(self) -> None:
        # hand-2 形态：标题 + 侧栏 showcase + 指标行 + 两块内容，需要深度 4。
        cards = parse_cards(
            "<textCard><p>t</p></textCard>"
            "<showcaseCard><p>s</p></showcaseCard>"
            "<targetStatCard><value>1</value></targetStatCard>"
            "<targetStatCard><value>2</value></targetStatCard>"
            "<targetStatCard><value>3</value></targetStatCard>"
            "<Topology><p>a</p></Topology>"
            "<contentSummaryCard><p>b</p></contentSummaryCard>"
        )
        canvas = Canvas(1936, 1144)
        human = node_from_dict(
            {
                "kind": "column",
                "children": [
                    {"kind": "card", "cardIndex": 0},
                    {
                        "kind": "row",
                        "children": [
                            {"kind": "card", "cardIndex": 1},
                            {
                                "kind": "column",
                                "children": [
                                    {
                                        "kind": "row",
                                        "children": [
                                            {"kind": "card", "cardIndex": 2},
                                            {"kind": "card", "cardIndex": 3},
                                            {"kind": "card", "cardIndex": 4},
                                        ],
                                    },
                                    {
                                        "kind": "row",
                                        "children": [
                                            {"kind": "card", "cardIndex": 5},
                                            {"kind": "card", "cardIndex": 6},
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        )
        assert isinstance(human, ContainerNode)
        candidates = generate_candidates(cards, canvas, beam_width=256)
        keys = {canonical_key(tree) for tree in candidates}
        self.assertIn(canonical_key(human), keys)

    def test_geometry_respects_min_widths_and_fills_canvas(self) -> None:
        cards = parse_cards(SOURCE)
        canvas = Canvas(1024, 768)
        tree = ContainerNode(
            "row",
            (
                CardNode(0),
                ContainerNode(
                    "column", (CardNode(1), CardNode(2), CardNode(3))
                ),
            ),
        )
        geometry = layout_geometry(tree, cards, canvas)
        for card in cards:
            rect = geometry.card_rects[card.index]
            self.assertGreaterEqual(rect.x, 0)
            self.assertGreaterEqual(rect.y, 0)
            self.assertLessEqual(rect.x + rect.width, canvas.width + 1e-6)
            self.assertLessEqual(rect.y + rect.height, canvas.height + 1e-6)
        # 行分配应给子块保底最小宽，而不是按权重压没。
        col_min_width, _ = min_size(tree.children[1], cards, canvas.gap)
        self.assertGreaterEqual(
            geometry.card_rects[1].width, col_min_width - 1e-6
        )
        rects = list(geometry.card_rects.values())
        for i, a in enumerate(rects):
            for b in rects[i + 1 :]:
                overlap_x = max(
                    0.0, min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
                )
                overlap_y = max(
                    0.0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
                )
                self.assertAlmostEqual(overlap_x * overlap_y, 0.0, places=6)

    def test_type_group_scoring_prefers_grouped_stats(self) -> None:
        cards = parse_cards(SOURCE)
        canvas = Canvas(1024, 768)
        grouped = ContainerNode(
            "column",
            (
                CardNode(0),
                ContainerNode("row", (CardNode(1), CardNode(2))),
                CardNode(3),
            ),
        )
        split = ContainerNode(
            "column",
            (
                ContainerNode("row", (CardNode(0), CardNode(1))),
                ContainerNode("row", (CardNode(2), CardNode(3))),
            ),
        )
        _, grouped_penalties = score_tree(grouped, cards, canvas)
        _, split_penalties = score_tree(split, cards, canvas)
        self.assertLess(grouped_penalties["type_group"], split_penalties["type_group"])
        self.assertIn("header", grouped_penalties)
        self.assertIn("thin_banner", grouped_penalties)

    def test_grid_sequence_matches_frontend_format(self) -> None:
        import re

        cards = parse_cards(SOURCE)
        canvas = Canvas(1936, 1144)
        ranked = rank_layouts(cards, canvas, top_k=1, beam_width=64)
        sequence = tree_to_grid_sequence(ranked[0].tree, cards, canvas)
        self.assertIsNotNone(sequence)
        assert sequence is not None
        self.assertTrue(sequence.startswith("grid:8x5;"))
        tokens = re.findall(r"\((\d+),(\d+),(\d+),(\d+),([^,)]+)\)", sequence)
        self.assertEqual(len(tokens), len(cards))
        filled = set()
        for width, height, x, y, _typ in tokens:
            w, h, xx, yy = int(width), int(height), int(x), int(y)
            self.assertLessEqual(xx + w, 8)
            self.assertLessEqual(yy + h, 5)
            for cell_y in range(yy, yy + h):
                for cell_x in range(xx, xx + w):
                    self.assertNotIn((cell_x, cell_y), filled)
                    filled.add((cell_x, cell_y))
        self.assertEqual(len(filled), 40)
        payload = candidates_to_dict(ranked, cards, canvas)
        self.assertEqual(payload["candidates"][0]["gridSequence"], sequence)  # type: ignore[index]

    def test_uncoverable_reason_detects_leaf_order(self) -> None:
        target = ContainerNode(
            "row",
            (CardNode(0), CardNode(2), CardNode(1)),
        )
        self.assertEqual(uncoverable_reason(target, 3, 5), "leaf_order")

    def test_pipeline_returns_ranked_renderable_results(self) -> None:
        ranked = rank_layouts(
            self.cards,
            self.canvas,
            top_k=3,
            beam_width=64,
        )
        self.assertEqual(len(ranked), 3)
        self.assertEqual(
            [item.score for item in ranked],
            sorted(item.score for item in ranked),
        )
        rendered = render_psuip(ranked[0].tree, self.cards)
        self.assertIn("<layout:root>", rendered)
        self.assertIn('<layout:column alignItems="stretch">', rendered)
        self.assertEqual(rendered.count("<targetStatCard>"), 2)


if __name__ == "__main__":
    unittest.main()
