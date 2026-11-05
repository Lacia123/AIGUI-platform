"""本地 markdown 内容尺寸接口的 Python 客户端。

两个 HTTP 接口都跑在 ``localhost:3001``，作用不同：

1. ``check_layout`` → ``POST /api/markdown-layout-check``
   给定一张卡的裸 PSUIP 和提议 ``w×h``，回答「这个尺寸够不够展示」。
   只做是/否判定，不搜索更小或更大的格子。

2. ``check_min_size`` → ``POST /api/markdown-grid-growth-check``
   给定裸 PSUIP 和画布上界 ``columns×rows``，从较小格子向外生长，
   返回这份内容的最小可展示尺寸 ``min_w×min_h``。

同一 ``(psuip, 尺寸)`` 走进程内缓存。任一接口挂掉后本进程不再重试两者。
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

from . import config as cfg

_layout_cache: dict[tuple[str, int, int], dict[str, Any]] = {}
_growth_cache: dict[tuple[str, int, int], dict[str, Any]] = {}
_disabled_reason: str | None = None


def _warn(msg: str) -> None:
    print(f"[layout-check] {msg}", file=sys.stderr)


def reset_client() -> None:
    """清掉「接口挂了不再重试」标记，便于批量脚本在超时后继续。"""
    global _disabled_reason
    _disabled_reason = None


def _enabled() -> bool:
    return not _disabled_reason and bool(getattr(cfg, "LAYOUT_CHECK_ENABLED", True))


def _timeout() -> float:
    return float(getattr(cfg, "LAYOUT_CHECK_TIMEOUT", 15.0))


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """POST JSON。成功或带 JSON 体的 HTTP 错误返回 dict；其它失败返回 None。"""
    global _disabled_reason
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            _warn(f"HTTP {exc.code}: {exc.reason}")
            _disabled_reason = f"http {exc.code}"
            return None
    except Exception as exc:
        _warn(f"unreachable {url}: {exc}; 本进程跳过后续 layout-check")
        _disabled_reason = str(exc)
        return None


def _messages(payload: dict[str, Any]) -> list[str]:
    details = payload.get("details") or {}
    raw = details.get("messages") or []
    if raw:
        return [str(item) for item in raw]
    if payload.get("error"):
        return [str(payload["error"])]
    return []


def _valid_from_payload(payload: dict[str, Any]) -> bool | None:
    if payload.get("success", True):
        return bool(payload.get("valid"))
    return False


def check_layout(
    psuip: str,
    width: int,
    height: int,
    *,
    test: bool = False,
) -> dict[str, Any]:
    """判定裸 PSUIP 在给定 ``width×height`` 格内是否内容可见。

    对应 ``POST /api/markdown-layout-check``。问的是「这个尺寸行不行」，
    不返回最小尺寸。

    返回:
        reachable: 接口是否成功响应
        valid: True/False；不可达时为 None
        messages: details.messages
    """
    key = (psuip, int(width), int(height))
    hit = _layout_cache.get(key)
    if hit is not None:
        return hit

    empty = {"reachable": False, "valid": None, "messages": []}
    if not _enabled():
        return empty
    if width < 1 or height < 1 or not psuip.strip():
        result = {
            "reachable": True,
            "valid": False,
            "messages": ["empty psuip or non-positive size"],
        }
        _layout_cache[key] = result
        return result

    url = str(getattr(cfg, "LAYOUT_CHECK_URL", "") or "").strip()
    payload = _post_json(
        url,
        {
            "psuip": psuip,
            "type": "grid",
            "width": int(width),
            "height": int(height),
            "test": bool(test),
        },
    )
    if payload is None:
        return empty

    result = {
        "reachable": True,
        "valid": _valid_from_payload(payload),
        "messages": _messages(payload),
    }
    _layout_cache[key] = result
    return result


def check_min_size(
    psuip: str,
    columns: int,
    rows: int,
    *,
    test: bool = False,
) -> dict[str, Any]:
    """在 ``columns×rows`` 上界内，求裸 PSUIP 的最小可展示格子尺寸。

    对应 ``POST /api/markdown-grid-growth-check``。服务从较小格子向外生长，
    响应里的 ``columns`` / ``rows`` 即最小展示宽高。

    返回:
        reachable: 接口是否成功响应
        valid: 在上界内是否找到可展示尺寸；不可达时为 None
        min_w / min_h: 最小展示格数；找不到或不可达时为 None
        start_w / start_h: 生长起点
        max_w / max_h: 本次请求的上界
        tendency: 优先扩展方向，如 ``[[0,1],[1,0]]``
        card_name: 卡片标签名
        messages: details.messages
    """
    key = (psuip, int(columns), int(rows))
    hit = _growth_cache.get(key)
    if hit is not None:
        return hit

    empty = {
        "reachable": False,
        "valid": None,
        "min_w": None,
        "min_h": None,
        "start_w": None,
        "start_h": None,
        "max_w": None,
        "max_h": None,
        "tendency": [],
        "card_name": "",
        "messages": [],
    }
    if not _enabled():
        return empty
    if columns < 1 or rows < 1 or not psuip.strip():
        result = {
            **empty,
            "reachable": True,
            "valid": False,
            "max_w": int(columns) if columns >= 1 else None,
            "max_h": int(rows) if rows >= 1 else None,
            "messages": ["empty psuip or non-positive canvas"],
        }
        _growth_cache[key] = result
        return result

    url = str(getattr(cfg, "GRID_GROWTH_CHECK_URL", "") or "").strip()
    payload = _post_json(
        url,
        {
            "psuip": psuip,
            "columns": int(columns),
            "rows": int(rows),
            "test": bool(test),
        },
    )
    if payload is None:
        return empty

    valid = _valid_from_payload(payload)
    min_w = payload.get("columns")
    min_h = payload.get("rows")
    start_w = payload.get("startColumns")
    start_h = payload.get("startRows")
    result = {
        "reachable": True,
        "valid": valid,
        "min_w": int(min_w) if min_w is not None else None,
        "min_h": int(min_h) if min_h is not None else None,
        "start_w": int(start_w) if start_w is not None else None,
        "start_h": int(start_h) if start_h is not None else None,
        "max_w": int(payload["maxColumns"]) if payload.get("maxColumns") is not None else int(columns),
        "max_h": int(payload["maxRows"]) if payload.get("maxRows") is not None else int(rows),
        "tendency": list(payload.get("tendency") or []),
        "card_name": str(payload.get("cardName") or ""),
        "messages": _messages(payload),
    }
    _growth_cache[key] = result
    return result
