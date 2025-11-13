"""Advanced natural language analysis tools for regulatory content."""

from __future__ import annotations

import importlib
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Requirement:
    """Structured representation of a regulation requirement."""

    text: str
    entities: dict[str, Any]
    deadline: str | None
    penalties: str | None
    classification: str | None


class RegulationNLP:
    """NLP utilities for understanding regulation text."""

    def __init__(
        self,
        *,
        spacy_model: str = "en_core_web_sm",
        classifier_model: str = "nlpaueb/legal-bert-small-uncased",
    ) -> None:
        self._spacy = self._load_spacy(spacy_model)
        self._classifier = self._load_classifier(classifier_model)

    def extract_requirements(self, regulation_text: str) -> list[Requirement]:
        """Extract obligation-oriented sentences with contextual metadata."""

        doc = self._spacy(regulation_text)
        requirements: list[Requirement] = []
        for sentence in doc.sents:
            if self._is_requirement_sentence(sentence.text):
                classification = self.classify_requirement(sentence.text)
                requirement = Requirement(
                    text=sentence.text.strip(),
                    entities=self.extract_entities(sentence),
                    deadline=self.extract_deadlines(sentence.text),
                    penalties=self.extract_penalties(sentence.text),
                    classification=classification,
                )
                requirements.append(requirement)
        return requirements

    def classify_requirement(self, text: str) -> str | None:
        """Classify a requirement sentence using the configured transformer pipeline."""

        if not self._classifier:
            return None
        try:
            predictions = self._classifier(text, truncation=True)
        except Exception as exc:  # pragma: no cover - dependent on external model availability
            logger.warning("Classifier prediction failed: %s", exc)
            return None

        if isinstance(predictions, list) and predictions:
            prediction = predictions[0]
            if isinstance(prediction, dict):
                return prediction.get("label")
        return None

    def extract_entities(self, sentence) -> dict[str, Any]:  # type: ignore[override]
        """Extract named entities such as amounts, organizations, and dates."""

        entities: dict[str, Any] = {}
        for ent in sentence.ents:
            if ent.label_ in {"MONEY", "PERCENT"}:
                entities["amount"] = ent.text
            elif ent.label_ in {"DATE", "TIME"}:
                entities["date"] = ent.text
            elif ent.label_ in {"ORG", "GPE"}:
                entities.setdefault("organizations", set()).add(ent.text)
        if "organizations" in entities:
            entities["organizations"] = sorted(entities["organizations"])  # type: ignore[index]
        return entities

    def extract_deadlines(self, text: str) -> str | None:
        """Find deadline phrases using simple pattern matching."""

        deadline_patterns = [
            r"within\s+\d+\s+(days|weeks|months)",
            r"no\s+later\s+than\s+[\w\s]+",
            r"by\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"by\s+\d{1,2}/\d{1,2}/\d{2,4}",
        ]
        for pattern in deadline_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def extract_penalties(self, text: str) -> str | None:
        """Extract penalty descriptors from requirement text."""

        penalty_patterns = [
            r"subject to (?:a )?fine[s]? of [^\.]+",
            r"penalty of [^\.]+",
            r"may result in suspension",
            r"license may be revoked",
        ]
        for pattern in penalty_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _is_requirement_sentence(self, text: str) -> bool:
        keywords = ("must", "shall", "required", "comply", "ensure", "obligated")
        lowered = text.lower()
        return any(keyword in lowered for keyword in keywords)

    def _load_spacy(self, model: str):
        spacy_module = importlib.import_module("spacy")
        try:
            return spacy_module.load(model)
        except OSError:  # pragma: no cover - depends on runtime model availability
            logger.warning("spaCy model %s not found. Falling back to en_core_web_sm.", model)
            return spacy_module.load("en_core_web_sm")

    def _load_classifier(self, model: str):
        try:
            transformers = importlib.import_module("transformers")
        except ModuleNotFoundError:  # pragma: no cover - optional dependency
            logger.warning(
                "transformers library not installed; requirement classification disabled."
            )
            return None

        pipeline = transformers.pipeline
        try:
            return pipeline("text-classification", model=model)
        except Exception as exc:  # pragma: no cover - remote download may fail
            logger.warning("Unable to initialize classification pipeline: %s", exc)
            return None


__all__ = ["RegulationNLP", "Requirement"]
