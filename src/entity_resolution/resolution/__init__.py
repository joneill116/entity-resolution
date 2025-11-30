"""
Entity resolution algorithms and matching.

This module provides the matching algorithms and strategies
used for entity resolution.
"""

from entity_resolution.resolution.matchers import (
    BaseMatcher,
    CompositeMatcher,
    IdentifierMatcher,
    MatchConfig,
    NameMatcher,
)

__all__ = [
    "BaseMatcher",
    "CompositeMatcher",
    "IdentifierMatcher",
    "MatchConfig",
    "NameMatcher",
]
