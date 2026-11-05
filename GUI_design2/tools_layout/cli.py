"""布局候选生成命令行入口。

用法：
    python -m tools_layout.cli generate input.cards.psuip.md --width 390 --height 844
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from .domain import Canvas
from .evaluation import evaluate_dataset
from .parser import parse_card_file
from .pipeline import candidates_to_dict, rank_layouts, write_results


def _generate(args: argparse.Namespace) -> int:
    cards = parse_card_file(args.input)
    canvas = Canvas(args.width, args.height, args.gap)
    candidates = rank_layouts(
        cards,
        canvas,
        top_k=args.top_k,
        max_depth=args.max_depth,
        beam_width=args.beam_width,
    )
    result = candidates_to_dict(candidates, cards, canvas)
    if args.output:
        result_path = write_results(args.output, candidates, cards, canvas)
        result["resultFile"] = str(result_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    result = evaluate_dataset(
        args.dataset,
        beam_width=args.beam_width,
        max_depth=args.max_depth,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _select(args: argparse.Namespace) -> int:
    source_path = Path(args.candidates)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    if args.rank < 1 or args.rank > len(candidates):
        raise ValueError(f"rank 应在 1..{len(candidates)} 之间")
    record = {
        "recordedAt": datetime.now(UTC).isoformat(),
        "source": str(source_path),
        "canvas": payload.get("canvas"),
        "cardCount": payload.get("cardCount"),
        "selectedRank": args.rank,
        "selected": candidates[args.rank - 1],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tools_layout",
        description="为有序 Card 生成并评分 row/column 布局树",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成 Top-K 布局")
    generate.add_argument("input", help="Card-only PSUIP 文件")
    generate.add_argument("--width", type=float, required=True)
    generate.add_argument("--height", type=float, required=True)
    generate.add_argument("--gap", type=float, default=16)
    generate.add_argument("--top-k", type=int, default=3)
    generate.add_argument("--max-depth", type=int, default=5)
    generate.add_argument("--beam-width", type=int, default=256)
    generate.add_argument("--output", help="同时写入候选 JSON 和 PSUIP 的目录")
    generate.set_defaults(handler=_generate)

    default_dataset = (
        Path(__file__).resolve().parents[1]
        / "layout2data"
        / "flex_layouts.jsonl"
    )
    evaluate = subparsers.add_parser("evaluate", help="在现有布局集上评估排名")
    evaluate.add_argument(
        "--dataset",
        default=str(default_dataset),
        help="flex_layouts.json 或 jsonl",
    )
    evaluate.add_argument("--beam-width", type=int, default=256)
    evaluate.add_argument("--max-depth", type=int, default=5)
    evaluate.add_argument("--limit", type=int)
    evaluate.set_defaults(handler=_evaluate)

    select = subparsers.add_parser("select", help="记录一次人工候选选择")
    select.add_argument("candidates", help="generate 生成的 candidates.json")
    select.add_argument("--rank", type=int, required=True)
    select.add_argument(
        "--output",
        default="layout2data/selections.jsonl",
        help="选择记录 JSONL",
    )
    select.set_defaults(handler=_select)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
