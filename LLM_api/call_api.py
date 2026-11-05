"""调用阿里云百炼 OpenAI 兼容接口。

先填写 API_KEY 和 MODEL，或通过环境变量 DASHSCOPE_API_KEY、
DASHSCOPE_MODEL 提供。API Key 不要提交到版本库。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


API_KEY = "sk-ws-H.EDYRMHY.jTfk.MEUCICZZOioZ6Cp6CVxXD3YlJ8hM4SY27veJoTg7-zmMDo1rAiEAlQYbl1Po9fqQS9BW9YBd_o0H-ZIV8B5ng-MTM_VNbSs"
MODEL = "qwen3.7-max"
BASE_URL = (
    "https://ws-tmkcdzwnoe6l94sp.cn-beijing.maas.aliyuncs.com"
    "/compatible-mode/v1"
)


def main() -> None:
    api_key = os.getenv("DASHSCOPE_API_KEY", API_KEY).strip()
    model = os.getenv("DASHSCOPE_MODEL", MODEL).strip()

    if not api_key:
        raise SystemExit(
            "API Key 为空：请填写 API_KEY，或设置环境变量 DASHSCOPE_API_KEY。"
        )
    if not model:
        raise SystemExit(
            "模型名为空：请填写 MODEL，或设置环境变量 DASHSCOPE_MODEL。"
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你好"},
            {"role": "user", "content": "请回复一句简短的话。"},
        ],
        "temperature": 0.7,
    }
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"请求失败: {exc.reason}") from exc

    try:
        print(result["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
