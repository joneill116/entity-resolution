"""
Unit tests for data models.
"""

from entity_resolution.models import (
    ConfidenceLevel,
    DataSource,
    Entity,
    EntityMatch,
    EntityType,
    Identifier,
    SourceEntity,
)


class TestIdentifier:
    """Tests for the Identifier model."""

    def test_create_identifier(self):
        """Test creating an identifier."""
        identifier = Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
        assert identifier.source == DataSource.BLOOMBERG
        assert identifier.id_type == "ISIN"
        assert identifier.value == "US0378331005"

    def test_identifier_is_hashable(self):
        """Test that identifiers are hashable for use in sets."""
        id1 = Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
        id2 = Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")

        # Same values should hash equally
        assert hash(id1) == hash(id2)

        # Can be used in sets
        id_set = {id1, id2}
        assert len(id_set) == 1


class TestSourceEntity:
    """Tests for the SourceEntity model."""

    def test_create_source_entity(self):
        """Test creating a source entity."""
        entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="BBG000B9XRY4",
            entity_type=EntityType.COMPANY,
            name="Apple Inc.",
            alternate_names=["APPLE INC", "Apple Computer Inc"],
        )

        assert entity.source == DataSource.BLOOMBERG
        assert entity.source_id == "BBG000B9XRY4"
        assert entity.entity_type == EntityType.COMPANY
        assert entity.name == "Apple Inc."
        assert len(entity.alternate_names) == 2

    def test_all_names_property(self):
        """Test the all_names property."""
        entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="123",
            name="Primary Name",
            alternate_names=["Alt Name 1", "Alt Name 2"],
        )

        all_names = entity.all_names
        assert len(all_names) == 3
        assert "Primary Name" in all_names
        assert "Alt Name 1" in all_names
        assert "Alt Name 2" in all_names


class TestEntity:
    """Tests for the canonical Entity model."""

    def test_create_entity(self):
        """Test creating a canonical entity."""
        entity = Entity(entity_type=EntityType.COMPANY, canonical_name="Apple Inc.")

        assert entity.canonical_name == "Apple Inc."
        assert entity.entity_type == EntityType.COMPANY
        assert entity.id is not None  # UUID should be auto-generated

    def test_add_source_entity(self):
        """Test adding source entities to a canonical entity."""
        canonical = Entity(entity_type=EntityType.COMPANY, canonical_name="Apple Inc.")

        source1 = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="BBG000B9XRY4",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )

        source2 = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="4295905573",
            name="Apple Inc",
            alternate_names=["AAPL US"],
        )

        canonical.add_source_entity(source1)
        canonical.add_source_entity(source2)

        assert len(canonical.source_entities) == 2
        assert DataSource.BLOOMBERG in canonical.sources
        assert DataSource.REFINITIV in canonical.sources
        assert len(canonical.identifiers) == 1

    def test_sources_property(self):
        """Test the sources property."""
        canonical = Entity(canonical_name="Test Corp")

        canonical.add_source_entity(
            SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Test")
        )
        canonical.add_source_entity(
            SourceEntity(source=DataSource.MSCI, source_id="2", name="Test")
        )

        sources = canonical.sources
        assert len(sources) == 2
        assert DataSource.BLOOMBERG in sources
        assert DataSource.MSCI in sources


class TestEntityMatch:
    """Tests for the EntityMatch model."""

    def test_create_match(self):
        """Test creating an entity match."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Apple Inc.")
        entity_b = SourceEntity(source=DataSource.REFINITIV, source_id="2", name="Apple Inc")

        match = EntityMatch(
            entity_a=entity_a,
            entity_b=entity_b,
            similarity_score=0.95,
            confidence=ConfidenceLevel.HIGH,
            match_reasons=["Name match", "Identifier match"],
        )

        assert match.similarity_score == 0.95
        assert match.confidence == ConfidenceLevel.HIGH
        assert len(match.match_reasons) == 2

    def test_is_high_confidence(self):
        """Test the is_high_confidence property."""
        entity_a = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Test")
        entity_b = SourceEntity(source=DataSource.REFINITIV, source_id="2", name="Test")

        high_match = EntityMatch(
            entity_a=entity_a,
            entity_b=entity_b,
            similarity_score=0.95,
            confidence=ConfidenceLevel.HIGH,
        )
        assert high_match.is_high_confidence

        low_match = EntityMatch(
            entity_a=entity_a,
            entity_b=entity_b,
            similarity_score=0.6,
            confidence=ConfidenceLevel.LOW,
        )
        assert not low_match.is_high_confidence

        # Score >= 0.9 should also be high confidence
        score_match = EntityMatch(
            entity_a=entity_a,
            entity_b=entity_b,
            similarity_score=0.92,
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert score_match.is_high_confidence
