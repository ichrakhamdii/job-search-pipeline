import os
import time

import requests

API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Fallback only - see embedder.py's DEFAULT_API_KEY comment. A multi-user server MUST pass
# api_key explicitly on every call instead of relying on this.
DEFAULT_API_KEY = os.environ.get("GROQ_API_KEY", "")
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_RETRIES = 3


def is_configured(api_key: str | None = None) -> bool:
    return bool(api_key or DEFAULT_API_KEY)


def call_groq(system_prompt: str, user_prompt: str, api_key: str | None = None,
              model: str | None = None, temperature: float = 0.2,
              log_prefix: str = "groq") -> dict:
    """Call Groq's OpenAI-compatible chat completions API in JSON mode, with retry on 429s.

    Returns the raw parsed response body; callers extract choices[0].message.content
    themselves and validate it against their own schema.

    api_key: pass explicitly in any multi-user context (e.g. a web backend). Falls back
    to GROQ_API_KEY from the environment for single-user CLI use.
    """
    key = api_key or DEFAULT_API_KEY
    if not key:
        raise RuntimeError("Groq API key not provided (pass api_key= or set GROQ_API_KEY).")
    model = model or DEFAULT_MODEL

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": temperature,
    }
    for attempt in range(MAX_RETRIES):
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 429 and attempt < MAX_RETRIES - 1:
            wait = float(resp.headers.get("retry-after", 5 * (attempt + 1)))
            print(f"[{log_prefix}] Rate limited, retrying in {wait:.0f}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Groq API: exhausted retries")
