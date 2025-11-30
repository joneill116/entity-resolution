"""
Entity matching algorithms for resolution.

This module provides various matching strategies for comparing
entities and computing similarity scores.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from entity_resolution.models import ConfidenceLevel, EntityMatch, SourceEntity

if TYPE_CHECKING:
    pass


@dataclass
class MatchConfig:
    """Configuration for matching thresholds and weights."""

    # Minimum similarity score to consider a match
    min_similarity_threshold: float = 0.7

    # Weights for different matching components
    identifier_match_weight: float = 0.4
    name_match_weight: float = 0.35
    attribute_match_weight: float = 0.25

    # Threshold for high confidence matches
    high_confidence_threshold: float = 0.9
    medium_confidence_threshold: float = 0.75


class BaseMatcher(ABC):
    """Abstract base class for entity matchers."""

    @abstractmethod
    def compute_similarity(
        self, entity_a: SourceEntity, entity_b: SourceEntity
    ) -> tuple[float, dict[str, float], list[str]]:
        """
        Compute similarity between two entities.

        Args:
            entity_a: First entity.
            entity_b: Second entity.

        Returns:
            Tuple of (overall_score, component_scores, match_reasons)
        """
        pass

    def match(self, entity_a: SourceEntity, entity_b: SourceEntity) -> EntityMatch | None:
        """
        Attempt to match two entities.

        Args:
            entity_a: First entity.
            entity_b: Second entity.

        Returns:
            EntityMatch if entities match, None otherwise.
        """
        score, components, reasons = self.compute_similarity(entity_a, entity_b)

        if score < self.config.min_similarity_threshold:
            return None

        # Determine confidence level
        if score >= self.config.high_confidence_threshold:
            confidence = ConfidenceLevel.HIGH
        elif score >= self.config.medium_confidence_threshold:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        return EntityMatch(
            entity_a=entity_a,
            entity_b=entity_b,
            similarity_score=score,
            confidence=confidence,
            match_reasons=reasons,
            component_scores=components,
        )

    @property
    def config(self) -> MatchConfig:
        """Get the matcher configuration."""
        return getattr(self, "_config", MatchConfig())


class IdentifierMatcher(BaseMatcher):
    """
    Matcher that compares entity identifiers.

    Identifiers like LEI, ISIN, CUSIP provide strong evidence
    for entity matches.
    """

    # Priority order for identifier comparison (higher = more reliable)
    IDENTIFIER_PRIORITY = {
        "LEI": 1.0,
        "ISIN": 0.95,
        "FIGI": 0.9,
        "CUSIP": 0.85,
        "SEDOL": 0.85,
        "TICKER": 0.6,
    }

    def __init__(self, config: MatchConfig | None = None):
        self._config = config or MatchConfig()

    def compute_similarity(
        self, entity_a: SourceEntity, entity_b: SourceEntity
    ) -> tuple[float, dict[str, float], list[str]]:
        """Compute identifier-based similarity."""
        component_scores = {}
        match_reasons = []
        max_score = 0.0

        # Build identifier maps
        ids_a = {(id_.id_type.upper(), id_.value.upper()): id_ for id_ in entity_a.identifiers}
        ids_b = {(id_.id_type.upper(), id_.value.upper()): id_ for id_ in entity_b.identifiers}

        # Find matching identifiers
        for key in ids_a:
            if key in ids_b:
                id_type = key[0]
                priority = self.IDENTIFIER_PRIORITY.get(id_type, 0.5)
                component_scores[f"identifier_{id_type}"] = priority
                match_reasons.append(f"Matching {id_type}: {key[1]}")
                max_score = max(max_score, priority)

        return max_score, component_scores, match_reasons


class NameMatcher(BaseMatcher):
    """
    Matcher that compares entity names using fuzzy matching.

    Uses multiple string similarity algorithms to handle
    variations in entity names.
    """

    def __init__(self, config: MatchConfig | None = None):
        self._config = config or MatchConfig()

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        if not name:
            return ""

        # Convert to uppercase
        normalized = name.upper()

        # Remove common corporate suffixes
        suffixes = [
            r"\s+INC\.?$",
            r"\s+LLC\.?$",
            r"\s+LTD\.?$",
            r"\s+CORP\.?$",
            r"\s+CO\.?$",
            r"\s+COMPANY$",
            r"\s+LIMITED$",
            r"\s+PLC\.?$",
            r"\s+S\.?A\.?$",
            r"\s+AG$",
            r"\s+GMBH$",
            r"\s+N\.?V\.?$",
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, "", normalized)

        # Remove punctuation and extra whitespace
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def compute_similarity(
        self, entity_a: SourceEntity, entity_b: SourceEntity
    ) -> tuple[float, dict[str, float], list[str]]:
        """Compute name-based similarity."""
        component_scores: dict[str, float] = {}
        match_reasons: list[str] = []

        # Get all names for both entities
        names_a = [self._normalize_name(n) for n in entity_a.all_names if n]
        names_b = [self._normalize_name(n) for n in entity_b.all_names if n]

        if not names_a or not names_b:
            return 0.0, component_scores, match_reasons

        # Find best name match
        best_score = 0.0
        best_pair = ("", "")

        for name_a in names_a:
            for name_b in names_b:
                # Use multiple fuzzy matching algorithms
                ratio = fuzz.ratio(name_a, name_b) / 100.0
                partial = fuzz.partial_ratio(name_a, name_b) / 100.0
                token_sort = fuzz.token_sort_ratio(name_a, name_b) / 100.0
                token_set = fuzz.token_set_ratio(name_a, name_b) / 100.0

                # Weighted combination
                score = 0.3 * ratio + 0.2 * partial + 0.25 * token_sort + 0.25 * token_set

                if score > best_score:
                    best_score = score
                    best_pair = (name_a, name_b)

        component_scores["name_similarity"] = best_score

        if best_score >= self._config.min_similarity_threshold:
            match_reasons.append(
                f"Name match ({best_score:.2%}): '{best_pair[0]}' ~ '{best_pair[1]}'"
            )

        return best_score, component_scores, match_reasons


class CompositeMatcher(BaseMatcher):
    """
    Composite matcher that combines multiple matching strategies.

    This is the primary matcher used for entity resolution,
    combining identifier and name matching with configurable weights.
    """

    def __init__(self, config: MatchConfig | None = None):
        self._config = config or MatchConfig()
        self.identifier_matcher = IdentifierMatcher(self._config)
        self.name_matcher = NameMatcher(self._config)

    def compute_similarity(
        self, entity_a: SourceEntity, entity_b: SourceEntity
    ) -> tuple[float, dict[str, float], list[str]]:
        """
        Compute composite similarity using multiple strategies.

        The overall score is a weighted combination of:
        - Identifier matching (highest weight for exact ID matches)
        - Name similarity (fuzzy matching)
        """
        component_scores = {}
        match_reasons = []

        # Get identifier score
        id_score, id_components, id_reasons = self.identifier_matcher.compute_similarity(
            entity_a, entity_b
        )
        component_scores.update(id_components)
        match_reasons.extend(id_reasons)

        # Get name score
        name_score, name_components, name_reasons = self.name_matcher.compute_similarity(
            entity_a, entity_b
        )
        component_scores.update(name_components)
        match_reasons.extend(name_reasons)

        # If we have a strong identifier match, use that
        if id_score >= 0.9:
            overall_score = id_score
            match_reasons.insert(0, "Strong identifier match")
        else:
            # Weighted combination
            overall_score = (
                self._config.identifier_match_weight * id_score
                + self._config.name_match_weight * name_score
            )
            # Normalize
            total_weight = self._config.identifier_match_weight + self._config.name_match_weight
            overall_score = overall_score / total_weight if total_weight > 0 else 0

        component_scores["overall"] = overall_score

        return overall_score, component_scores, match_reasons
