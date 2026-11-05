"""探测当前 API Key 可以调用的 Qwen 模型。

用法：
    $env:DASHSCOPE_API_KEY = "你的 API Key"
    python LLM_api/probe_qwen_models.py

默认探测模型目录中的全部 Qwen 模型，这会产生多次 API 请求，
可能产生费用或触发限流。添加 --stop-first 可在找到首个可用模型后停止。
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


API_KEY = "sk-ws-H.EDYRMHY.jTfk.MEUCICZZOioZ6Cp6CVxXD3YlJ8hM4SY27veJoTg7-zmMDo1rAiEAlQYbl1Po9fqQS9BW9YBd_o0H-ZIV8B5ng-MTM_VNbSs"
BASE_URL = (
    "https://ws-tmkcdzwnoe6l94sp.cn-beijing.maas.aliyuncs.com"
    "/compatible-mode/v1"
)


def request_json(
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    method = "GET"
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except urllib.error.URLError as exc:
        raise SystemExit(f"请求失败: {exc.reason}") from exc


def error_message(result: dict[str, Any] | str) -> str:
    if not isinstance(result, dict):
        return result
    error = result.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    return str(result)


def fetch_qwen_models(api_key: str) -> list[str]:
    status, result = request_json(f"{BASE_URL}/models", api_key)
    if status != 200 or not isinstance(result, dict):
        raise SystemExit(f"获取模型列表失败（HTTP {status}）：{error_message(result)}")

    models = []
    for item in result.get("data", []):
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if isinstance(model_id, str) and "qwen" in model_id.lower():
            models.append(model_id)
    return sorted(set(models), key=str.lower)


def probe_model(api_key: str, model: str) -> tuple[int, dict[str, Any] | str]:
    return request_json(
        f"{BASE_URL}/chat/completions",
        api_key,
        payload={
            "model": model,
            "messages": [{"role": "user", "content": "你好"}],
            "temperature": 0,
            "max_tokens": 1,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="探测可调用的 Qwen 模型")
    parser.add_argument(
        "--stop-first",
        action="store_true",
        help="找到第一个可用模型后立即停止",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="请求间隔秒数，默认 0.5",
    )
    args = parser.parse_args()

    api_key = os.getenv("DASHSCOPE_API_KEY", API_KEY).strip()
    if not api_key:
        raise SystemExit(
            "API Key 为空。请先设置环境变量：\n"
            '$env:DASHSCOPE_API_KEY = "你的 API Key"'
        )

    models = fetch_qwen_models(api_key)
    if not models:
        raise SystemExit("模型目录中没有找到名称包含 qwen 的模型。")

    print(f"发现 {len(models)} 个 Qwen 模型，开始探测……")
    available: list[str] = []
    for index, model in enumerate(models, start=1):
        status, result = probe_model(api_key, model)
        if status == 200:
            available.append(model)
            print(f"[{index}/{len(models)}] 可用  {model}")
            if args.stop_first:
                break
        elif status == 403:
            print(f"[{index}/{len(models)}] 无权限 {model}")
        elif status == 429:
            print(f"[{index}/{len(models)}] 已限流 {model}：{error_message(result)}")
            print("停止探测，请稍后重试或增大 --delay。")
            break
        elif status in (401, 402):
            raise SystemExit(
                f"HTTP {status}，API Key 或账户不可用：{error_message(result)}"
            )
        else:
            print(
                f"[{index}/{len(models)}] 未确定 {model} "
                f"(HTTP {status})：{error_message(result)}"
            )
        time.sleep(max(0.0, args.delay))

    if available:
        print("\n可用模型：")
        for model in available:
            print(f"  {model}")
        print(f'\n可设置：$env:DASHSCOPE_MODEL = "{available[0]}"')
    else:
        print("\n本次未发现可用模型。")


if __name__ == "__main__":
    main()
