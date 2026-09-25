import type { ApiKeys } from "./types";

// BYOK: these keys are the user's own (Voyage/Groq/Adzuna), never sent anywhere except our
// own backend on each request. Stored in this browser only (localStorage), never persisted
// server-side - consistent with the project's BYOK decision (see docs/WEBAPP_PLAN.md).
const STORAGE_KEY = "job_search_pipeline_api_keys";

export function loadApiKeys(): ApiKeys {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveApiKeys(keys: ApiKeys): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}
