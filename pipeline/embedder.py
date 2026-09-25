import os
import time
import requests

API_URL = "https://api.voyageai.com/v1/embeddings"
# Fallback only - read once at import for the single-user CLI. A multi-user server MUST
# pass api_key explicitly on every call instead of relying on this, since a module-level
# constant is shared across every concurrent request in that context.
DEFAULT_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
DEFAULT_MODEL = os.environ.get("VOYAGE_MODEL", "voyage-3.5")
BATCH_SIZE = 20
MAX_RETRIES = 4
# Voyage caps accounts without a payment method on file at 3 requests/minute, so a
# transient 429 needs a real wait (not a quick backoff) to clear.
RETRY_BACKOFF_SECONDS = [10, 20, 40, 60]


def is_configured(api_key: str | None = None) -> bool:
    return bool(api_key or DEFAULT_API_KEY)


def embed_texts(texts: list[str], input_type: str, api_key: str | None = None,
                 model: str | None = None) -> list[list[float]]:
    """Get semantic embeddings for a list of texts via the Voyage AI API.

    input_type should be "query" for the candidate-profile side of a comparison and
    "document" for the job-posting side - Voyage's asymmetric retrieval mode gives
    better similarity quality than embedding both sides identically.

    api_key: pass explicitly in any multi-user context (e.g. a web backend). Falls back
    to VOYAGE_API_KEY from the environment for single-user CLI use.
    """
    if not texts:
        return []
    key = api_key or DEFAULT_API_KEY
    if not key:
        raise RuntimeError("Voyage API key not provided (pass api_key= or set VOYAGE_API_KEY).")
    model = model or DEFAULT_MODEL

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        if i > 0:
            # Free-tier accounts are capped at 3 requests/minute - space out multi-batch calls.
            time.sleep(21)
        batch = texts[i:i + BATCH_SIZE]
        payload = {"input": batch, "model": model, "input_type": input_type}

        for attempt in range(MAX_RETRIES):
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait = float(resp.headers.get("retry-after", RETRY_BACKOFF_SECONDS[attempt]))
                print(f"[embedder] Rate limited (Voyage free-tier cap is 3 req/min), retrying in {wait:.0f}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break

        data = resp.json()
        vectors.extend(item["embedding"] for item in data["data"])
    return vectors
