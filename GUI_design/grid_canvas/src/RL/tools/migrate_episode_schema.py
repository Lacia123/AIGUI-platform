"""将旧 episode（cards/cards_wh/target_xy）迁移为 clean schema v3。

用法:
  python -m RL.tools.migrate_episode_schema RL/data/handcrafted_layouts.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def migrate_episode(ep: dict[str, Any]) -> dict[str, Any]:
    """返回 v3 episode；输入已是 v3 时原样返回副本。"""
    if int(ep.get("schema_version", 0)) == 3:
        return dict(ep)
    old_cards = list(ep.get("cards") or [])
    if not old_cards:
        raise ValueError(f"episode {ep.get('id', '<unknown>')}: 缺少旧 cards")
    old_queue = {
        str(c.get("id")): c for c in (ep.get("cards_wh") or [])
    }
    card_queue = []
    expert_cards = []
    for card in old_cards:
        cid = str(card["id"])
        queue = old_queue.get(cid, {})
        entry = {"id": cid}
        for key in ("type", "label", "color", "psuip"):
            value = card.get(key, queue.get(key))
            if value is not None:
                entry[key] = value
        card_queue.append(entry)
        expert_cards.append(
            {
                "id": cid,
                "w": int(card["w"]),
                "h": int(card["h"]),
                "x": int(card["x"]),
                "y": int(card["y"]),
            }
        )
    clean = {
        key: value
        for key, value in ep.items()
        if key not in {"cards", "cards_wh", "target_xy"}
    }
    clean.update(
        schema_version=3,
        card_queue=card_queue,
        expert_cards=expert_cards,
        n_cards=len(card_queue),
        area=sum(c["w"] * c["h"] for c in expert_cards),
    )
    return clean


def migrate_path(path: Path) -> None:
    """原地迁移 JSON 或 JSONL；写入前先完整解析，失败不覆盖。"""
    if path.suffix.lower() == ".jsonl":
        episodes = [
            migrate_episode(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        body = "".join(json.dumps(ep, ensure_ascii=False) + "\n" for ep in episodes)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("episodes"), list):
            payload["episodes"] = [migrate_episode(ep) for ep in payload["episodes"]]
            payload["version"] = "3.0"
            payload["n_episodes"] = len(payload["episodes"])
        else:
            payload = migrate_episode(payload)
        body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(body, encoding="utf-8")
    print(f"migrated {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        migrate_path(path)


if __name__ == "__main__":
    main()
