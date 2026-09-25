import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import embedder
from .international import detect_signals, signals_label

# Relative importance of each profile facet in the overall match score.
CATEGORY_WEIGHTS = {
    "skills": 0.35,
    "experience": 0.30,
    "projects": 0.15,
    "certifications": 0.10,
    "education": 0.10,
}

# A job matching this many distinct profile skills already counts as a full (100%) skills match.
# Dividing by the candidate's total skill count instead would unfairly cap real matches near
# 20-30%, since no single job posting ever mentions a candidate's entire skill inventory.
SKILL_MATCH_CAP = 8

# Only jobs scoring at or above this are worth suggesting.
MIN_MATCH_SCORE = 50.0


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def build_category_texts(profile: dict) -> dict:
    """Build one text blob per profile facet so each can be matched against a job independently."""
    skills_text = " ".join(profile.get("skills", []))

    experience_text = " ".join(
        f"{e.get('title', '')} {e.get('description', '')}"
        for e in profile.get("experience", [])
    )

    projects_text = " ".join(
        f"{p.get('title', '')} {p.get('technologies', '')} {p.get('description', '')}"
        for p in profile.get("projects", [])
    )

    certifications_text = " ".join(profile.get("certifications", []))

    education_text = " ".join(profile.get("education", []))

    return {
        "skills": _normalize(skills_text),
        "experience": _normalize(experience_text),
        "projects": _normalize(projects_text),
        "certifications": _normalize(certifications_text),
        "education": _normalize(education_text),
    }


def skill_overlap_score(profile_skills: list[str], job_text: str) -> tuple[float, list[str]]:
    """Capped recall: matching SKILL_MATCH_CAP distinct skills already means a perfect fit.

    Uses word-boundary matching, not plain substring containment - otherwise short skill
    names like "R" or "Git" false-positive inside unrelated words ("caREer", "diGITal").
    """
    job_text_l = _normalize(job_text)
    matched = [
        s for s in profile_skills
        if re.search(r"(?<!\w)" + re.escape(s.lower()) + r"(?!\w)", job_text_l)
    ]
    score = min(len(matched) / SKILL_MATCH_CAP, 1.0)
    return score, matched


def _min_max_normalize(values):
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _category_similarities_tfidf(categories: dict, category_names: list, job_texts: list) -> dict:
    corpus = [categories[c] for c in category_names] + job_texts
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform(corpus)

    n_categories = len(category_names)
    category_vectors = matrix[:n_categories]
    job_vectors = matrix[n_categories:]

    return {
        name: cosine_similarity(category_vectors[i:i + 1], job_vectors).flatten()
        for i, name in enumerate(category_names)
    }


# Voyage's free tier (no payment method on file) caps requests at 10K tokens/minute -
# truncating each job text keeps a full batch well under that regardless of how long
# the original posting is.
EMBEDDING_TEXT_CHAR_LIMIT = 600


def _category_similarities_embeddings(categories: dict, category_names: list, job_texts: list,
                                       voyage_api_key: str | None) -> dict:
    category_texts = [categories[c] for c in category_names]
    truncated_job_texts = [t[:EMBEDDING_TEXT_CHAR_LIMIT] for t in job_texts]

    category_vectors = np.array(embedder.embed_texts(category_texts, input_type="query", api_key=voyage_api_key))
    job_vectors = np.array(embedder.embed_texts(truncated_job_texts, input_type="document", api_key=voyage_api_key))

    sims = cosine_similarity(category_vectors, job_vectors)
    return {name: sims[i] for i, name in enumerate(category_names)}


def rank_jobs(profile: dict, jobs: list[dict], top_n: int = 30,
              min_score: float = MIN_MATCH_SCORE, voyage_api_key: str | None = None) -> list[dict]:
    """Score each job against every facet of the candidate profile, on a real 0-100% scale.

    Semantic similarity per facet (skills, experience, projects, certifications, education) is
    computed via Voyage AI embeddings when VOYAGE_API_KEY is set (much better at catching
    synonyms - "computer vision" vs "image recognition" - than keyword overlap), falling back
    to TF-IDF cosine similarity otherwise. Each facet is min-max normalized across the current
    batch of jobs so the best-matching job for that facet reaches 100%. Skills additionally
    blend in a capped keyword-overlap ratio (exact tech-stack hits like "PyTorch" or "RAG" are
    strong signal on their own). Facets are combined with CATEGORY_WEIGHTS, a small bonus is
    added for visa/international/remote signals, and only jobs scoring >= min_score are returned.

    voyage_api_key: pass explicitly in any multi-user context. Falls back to VOYAGE_API_KEY
    from the environment for single-user CLI use.
    """
    if not jobs:
        return []

    categories = build_category_texts(profile)
    category_names = list(categories.keys())
    job_texts = [_normalize(f"{j.get('title','')} {j.get('description','')}") for j in jobs]

    if embedder.is_configured(voyage_api_key):
        raw_sims = _category_similarities_embeddings(categories, category_names, job_texts, voyage_api_key)
    else:
        print("[matcher] VOYAGE_API_KEY not set - falling back to TF-IDF keyword similarity.")
        raw_sims = _category_similarities_tfidf(categories, category_names, job_texts)

    norm_sims = {name: _min_max_normalize(values) for name, values in raw_sims.items()}

    results = []
    for idx, (job, job_text) in enumerate(zip(jobs, job_texts)):
        overlap, matched_skills = skill_overlap_score(profile.get("skills", []), job_text)
        skills_score = 0.6 * overlap + 0.4 * norm_sims["skills"][idx]

        category_scores = {"skills": skills_score}
        for name in ("experience", "projects", "certifications", "education"):
            category_scores[name] = norm_sims[name][idx]

        base_score = sum(CATEGORY_WEIGHTS[name] * score for name, score in category_scores.items())

        signals = detect_signals(job.get("title", ""), job.get("location", ""), job.get("description", ""))
        # Small bonus for candidates who need visa sponsorship / are applying internationally.
        bonus = (0.08 if signals["visa_sponsorship"] else 0) + \
                (0.04 if signals["international_candidates"] else 0) + \
                (0.03 if signals["remote_friendly"] else 0)
        final_score = min(base_score + bonus, 1.0)

        results.append({
            **job,
            "match_score": round(final_score * 100, 1),
            "skills_score": round(category_scores["skills"] * 100, 1),
            "experience_score": round(category_scores["experience"] * 100, 1),
            "projects_score": round(category_scores["projects"] * 100, 1),
            "certifications_score": round(category_scores["certifications"] * 100, 1),
            "education_score": round(category_scores["education"] * 100, 1),
            "matched_skills": ", ".join(matched_skills),
            "visa_sponsorship": signals["visa_sponsorship"],
            "international_candidates": signals["international_candidates"],
            "remote_friendly": signals["remote_friendly"],
            "international_signals": signals_label(signals),
        })

    results.sort(key=lambda r: r["match_score"], reverse=True)
    suggested = [r for r in results if r["match_score"] >= min_score]
    return suggested[:top_n]
