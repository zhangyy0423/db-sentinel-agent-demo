from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .config import OPENAI_BASE_URL, OPENAI_MODEL


def ask_openai_compatible(
    prompt: str,
    *,
    system_prompt: str = "你是只读数据库分析值班 Agent，只返回简洁、可审计的 JSON。",
    temperature: float = 0.1,
) -> str | None:
    """Best-effort OpenAI-compatible call. Demo stays usable without a key."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = OPENAI_MODEL
    base_url = OPENAI_BASE_URL.rstrip("/")
    if not api_key or not model:
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except (KeyError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return None
