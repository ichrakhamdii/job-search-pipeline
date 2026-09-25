import re

VISA_SPONSORSHIP_PATTERNS = [
    r"visa sponsorship", r"sponsors? (?:work )?visa", r"visa support",
    r"work permit sponsorship", r"h-?1b sponsorship", r"will sponsor",
    r"able to sponsor", r"relocation assistance", r"relocation package",
    r"relocation support", r"provide relocation",
]

INTERNATIONAL_CANDIDATE_PATTERNS = [
    r"international candidates", r"candidates worldwide", r"candidates from any country",
    r"open to candidates? (?:based )?(?:anywhere|globally|worldwide)",
    r"work from anywhere", r"anywhere in the world", r"global remote", r"worldwide remote",
    r"remote[- ]first", r"remote[- ]anywhere", r"hire internationally", r"hiring globally",
    r"no visa required", r"regardless of location",
]

REMOTE_PATTERNS = [
    r"\bremote\b", r"work from home", r"distributed team", r"fully remote", r"100% remote",
]


def detect_signals(*texts: str) -> dict:
    """Scan job text (title, location, description) for international-friendliness signals."""
    combined = " ".join(t or "" for t in texts).lower()
    return {
        "visa_sponsorship": any(re.search(p, combined) for p in VISA_SPONSORSHIP_PATTERNS),
        "international_candidates": any(re.search(p, combined) for p in INTERNATIONAL_CANDIDATE_PATTERNS),
        "remote_friendly": any(re.search(p, combined) for p in REMOTE_PATTERNS),
    }


def signals_label(signals: dict) -> str:
    labels = []
    if signals.get("visa_sponsorship"):
        labels.append("Visa sponsorship")
    if signals.get("international_candidates"):
        labels.append("International candidates")
    if signals.get("remote_friendly"):
        labels.append("Remote")
    return ", ".join(labels)
