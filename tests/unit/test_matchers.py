"""
Unit tests for entity matchers.
"""

import pytest

from entity_resolution.models import DataSource, Identifier, SourceEntity
from entity_resolution.resolution.matchers import (
    CompositeMatcher,
    IdentifierMatcher,
    MatchConfig,
    NameMatcher,
)


class TestIdentifierMatcher:
    """Tests for identifier-based matching."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return IdentifierMatcher()

    def test_exact_lei_match(self, matcher):
        """Test matching by LEI identifier."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="LEI", value="HWUPKR0MPOU8FGXBT394")
            ],
        )
        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Apple Inc",
            identifiers=[
                Identifier(source=DataSource.REFINITIV, id_type="LEI", value="HWUPKR0MPOU8FGXBT394")
            ],
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score == 1.0  # LEI has highest priority
        assert "LEI" in reasons[0]

    def test_isin_match(self, matcher):
        """Test matching by ISIN identifier."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )
        entity_b = SourceEntity(
            source=DataSource.MSCI,
            source_id="2",
            name="Apple",
            identifiers=[Identifier(source=DataSource.MSCI, id_type="ISIN", value="US0378331005")],
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score == 0.95  # ISIN priority
        assert "ISIN" in reasons[0]

    def test_no_matching_identifiers(self, matcher):
        """Test when no identifiers match."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Company A",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US1111111111")
            ],
        )
        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Company B",
            identifiers=[
                Identifier(source=DataSource.REFINITIV, id_type="ISIN", value="US2222222222")
            ],
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score == 0.0
        assert len(reasons) == 0


class TestNameMatcher:
    """Tests for name-based matching."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return NameMatcher()

    def test_exact_name_match(self, matcher):
        """Test exact name matching."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(source=DataSource.REFINITIV, source_id="2", name="Apple Inc.")

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score >= 0.9  # Should be very high

    def test_similar_name_match(self, matcher):
        """Test fuzzy name matching."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(
            source=DataSource.REFINITIV, source_id="2", name="Apple Incorporated"
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score >= 0.6  # Should still match reasonably well

    def test_alternate_name_match(self, matcher):
        """Test matching using alternate names."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            alternate_names=["AAPL US"],
        )
        entity_b = SourceEntity(source=DataSource.REFINITIV, source_id="2", name="AAPL US Equity")

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        # Should find match through alternate name
        assert score > 0

    def test_different_names(self, matcher):
        """Test non-matching names."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(
            source=DataSource.REFINITIV, source_id="2", name="Microsoft Corporation"
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score < 0.5  # Should not match well


class TestCompositeMatcher:
    """Tests for composite matching."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return CompositeMatcher()

    def test_identifier_takes_precedence(self, matcher):
        """Test that strong identifier match dominates."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="LEI", value="HWUPKR0MPOU8FGXBT394")
            ],
        )
        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="AAPL",  # Different name
            identifiers=[
                Identifier(source=DataSource.REFINITIV, id_type="LEI", value="HWUPKR0MPOU8FGXBT394")
            ],
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score >= 0.9  # LEI match should dominate
        assert "Strong identifier match" in reasons

    def test_combined_matching(self, matcher):
        """Test combined identifier and name matching."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[Identifier(source=DataSource.BLOOMBERG, id_type="TICKER", value="AAPL")],
        )
        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Apple Inc",
            identifiers=[Identifier(source=DataSource.REFINITIV, id_type="TICKER", value="AAPL")],
        )

        score, components, reasons = matcher.compute_similarity(entity_a, entity_b)

        assert score > 0.7
        assert "identifier_TICKER" in components
        assert "name_similarity" in components

    def test_match_method(self, matcher):
        """Test the match method returns EntityMatch."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )
        entity_b = SourceEntity(
            source=DataSource.MSCI,
            source_id="2",
            name="Apple Inc",
            identifiers=[Identifier(source=DataSource.MSCI, id_type="ISIN", value="US0378331005")],
        )

        match = matcher.match(entity_a, entity_b)

        assert match is not None
        assert match.similarity_score >= 0.7
        assert match.entity_a == entity_a
        assert match.entity_b == entity_b

    def test_no_match_below_threshold(self, matcher):
        """Test that low similarity doesn't create a match."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(
            source=DataSource.REFINITIV, source_id="2", name="Microsoft Corporation"
        )

        match = matcher.match(entity_a, entity_b)

        assert match is None


class TestMatchConfig:
    """Tests for match configuration."""

    def test_custom_threshold(self):
        """Test custom threshold configuration."""
        config = MatchConfig(min_similarity_threshold=0.8)
        matcher = CompositeMatcher(config=config)

        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Apple Inc Corp",  # Similar but not exact
        )

        match = matcher.match(entity_a, entity_b)

        # With higher threshold, marginal matches should be rejected
        if match:
            assert match.similarity_score >= 0.8
