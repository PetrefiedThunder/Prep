"""Semantic filtering helpers for gazette discovery."""
from __future__ import annotations

from typing import Iterable

from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "distiluse-base-multilingual-cased-v2"
_model: SentenceTransformer | None = None
_domain_embeddings = None
_DOMAIN_QUERIES = [
    "food safety",
    "commercial kitchen",
    "hygiene regulation",
    "cold storage",
    "grease trap",
    "health inspection",
    "temporary food establishment",
    "allergen labelling",
    "HACCP",
    "sanitation plan",
]


def _model_load() -> tuple[SentenceTransformer, any]:  # type: ignore[valid-type]
    global _model, _domain_embeddings
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        _domain_embeddings = _model.encode(
            _DOMAIN_QUERIES, normalize_embeddings=True
        )
    return _model, _domain_embeddings


def keep_relevant(candidates: Iterable[dict], threshold: float = 0.45) -> list[dict]:
    """Filter candidate gazette links using multilingual semantic similarity."""

    model, domain = _model_load()
    texts = [candidate.get("title") or candidate.get("snippet", "") for candidate in candidates]
    if not texts:
        return []
    vectors = model.encode(texts, normalize_embeddings=True)
    scores = util.cos_sim(vectors, domain).max(dim=1).values.tolist()
    filtered: list[dict] = []
    for candidate, score in zip(candidates, scores):
        if score >= threshold:
            enriched = dict(candidate)
            enriched["semantic_score"] = float(score)
            filtered.append(enriched)
    filtered.sort(key=lambda item: item["semantic_score"], reverse=True)
    return filtered


__all__ = ["keep_relevant", "MODEL_NAME"]
