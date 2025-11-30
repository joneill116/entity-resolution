"""
Integration tests for the entity resolution workflow.
"""

import pytest

from entity_resolution import EntityResolver, KnowledgeGraph
from entity_resolution.adapters import BloombergAdapter, MSCIAdapter, RefinitivAdapter
from entity_resolution.models import (
    DataSource,
    EntityType,
    Identifier,
    SourceEntity,
)


class TestEntityResolver:
    """Integration tests for EntityResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a fresh resolver instance."""
        return EntityResolver()

    def test_add_single_entity(self, resolver):
        """Test adding a single entity."""
        entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="BBG000B9XRY4",
            name="Apple Inc.",
            entity_type=EntityType.COMPANY,
        )

        resolver.add_entity(entity)

        assert resolver.entity_count == 1

    def test_add_multiple_entities(self, resolver):
        """Test adding multiple entities."""
        entities = [
            SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Company A"),
            SourceEntity(source=DataSource.REFINITIV, source_id="2", name="Company B"),
            SourceEntity(source=DataSource.MSCI, source_id="3", name="Company C"),
        ]

        count = resolver.add_entities(entities)

        assert count == 3
        assert resolver.entity_count == 3

    def test_resolve_matching_entities(self, resolver):
        """Test resolving entities that should match."""
        # Add matching entities from different sources
        bloomberg_entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="BBG000B9XRY4",
            name="Apple Inc.",
            entity_type=EntityType.COMPANY,
            identifiers=[
                Identifier(
                    source=DataSource.BLOOMBERG, id_type="LEI", value="HWUPKR0MPOU8FGXBT394"
                ),
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005"),
            ],
        )

        refinitiv_entity = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="4295905573",
            name="Apple Inc",
            entity_type=EntityType.COMPANY,
            identifiers=[
                Identifier(
                    source=DataSource.REFINITIV, id_type="LEI", value="HWUPKR0MPOU8FGXBT394"
                ),
                Identifier(source=DataSource.REFINITIV, id_type="ISIN", value="US0378331005"),
            ],
        )

        resolver.add_entities([bloomberg_entity, refinitiv_entity])
        results = resolver.resolve()

        # Should resolve to a single canonical entity
        assert len(results) == 1
        canonical = results[0].canonical_entity
        assert len(canonical.source_entities) == 2
        assert DataSource.BLOOMBERG in canonical.sources
        assert DataSource.REFINITIV in canonical.sources

    def test_resolve_non_matching_entities(self, resolver):
        """Test that non-matching entities stay separate."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )

        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Microsoft Corporation",
            identifiers=[
                Identifier(source=DataSource.REFINITIV, id_type="ISIN", value="US5949181045")
            ],
        )

        resolver.add_entities([entity_a, entity_b])
        results = resolver.resolve()

        # Should have two separate canonical entities
        assert len(results) == 2

    def test_multi_source_resolution(self, resolver):
        """Test resolution across multiple sources."""
        # Same company from four different sources
        entities = [
            SourceEntity(
                source=DataSource.BLOOMBERG,
                source_id="bbg1",
                name="Apple Inc.",
                identifiers=[
                    Identifier(source=DataSource.BLOOMBERG, id_type="LEI", value="LEI12345")
                ],
            ),
            SourceEntity(
                source=DataSource.REFINITIV,
                source_id="ref1",
                name="Apple Inc",
                identifiers=[
                    Identifier(source=DataSource.REFINITIV, id_type="LEI", value="LEI12345")
                ],
            ),
            SourceEntity(
                source=DataSource.MSCI,
                source_id="msci1",
                name="APPLE INC",
                identifiers=[Identifier(source=DataSource.MSCI, id_type="LEI", value="LEI12345")],
            ),
            SourceEntity(
                source=DataSource.BURGISS,
                source_id="burg1",
                name="Apple, Inc.",
                identifiers=[
                    Identifier(source=DataSource.BURGISS, id_type="LEI", value="LEI12345")
                ],
            ),
        ]

        resolver.add_entities(entities)
        results = resolver.resolve()

        # Should resolve to one entity from four sources
        assert len(results) == 1
        canonical = results[0].canonical_entity
        assert len(canonical.source_entities) == 4
        assert len(canonical.sources) == 4

    def test_find_matches(self, resolver):
        """Test finding matches without full resolution."""
        entity_a = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Apple Inc.",
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )

        entity_b = SourceEntity(
            source=DataSource.REFINITIV,
            source_id="2",
            name="Apple Inc",
            identifiers=[
                Identifier(source=DataSource.REFINITIV, id_type="ISIN", value="US0378331005")
            ],
        )

        resolver.add_entities([entity_a, entity_b])
        matches = resolver.find_matches()

        assert len(matches) == 1
        assert matches[0].similarity_score > 0.7

    def test_get_statistics(self, resolver):
        """Test resolution statistics."""
        entities = [
            SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Company A"),
            SourceEntity(source=DataSource.BLOOMBERG, source_id="2", name="Company B"),
            SourceEntity(source=DataSource.REFINITIV, source_id="3", name="Company C"),
        ]

        resolver.add_entities(entities)
        resolver.resolve()
        stats = resolver.get_statistics()

        assert stats["source_entities"] == 3
        assert stats["entities_by_source"]["bloomberg"] == 2
        assert stats["entities_by_source"]["refinitiv"] == 1

    def test_export_graph(self, resolver):
        """Test graph export functionality."""
        entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="1",
            name="Test Company",
            entity_type=EntityType.COMPANY,
        )

        resolver.add_entity(entity)
        ttl = resolver.export_graph(format="turtle")

        assert "Test Company" in ttl
        assert "SourceEntity" in ttl


class TestKnowledgeGraph:
    """Integration tests for KnowledgeGraph."""

    @pytest.fixture
    def graph(self):
        """Create a fresh knowledge graph."""
        return KnowledgeGraph()

    def test_add_source_entity(self, graph):
        """Test adding a source entity to the graph."""
        entity = SourceEntity(
            source=DataSource.BLOOMBERG,
            source_id="BBG000B9XRY4",
            name="Apple Inc.",
            entity_type=EntityType.COMPANY,
            identifiers=[
                Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005")
            ],
        )

        uri = graph.add_source_entity(entity)

        assert uri is not None
        assert len(graph) > 0

    def test_get_entities_by_source(self, graph):
        """Test querying entities by source."""
        entity1 = SourceEntity(source=DataSource.BLOOMBERG, source_id="1", name="Company A")
        entity2 = SourceEntity(source=DataSource.BLOOMBERG, source_id="2", name="Company B")
        entity3 = SourceEntity(source=DataSource.REFINITIV, source_id="3", name="Company C")

        graph.add_source_entity(entity1)
        graph.add_source_entity(entity2)
        graph.add_source_entity(entity3)

        bloomberg_entities = list(graph.get_entities_by_source(DataSource.BLOOMBERG))

        assert len(bloomberg_entities) == 2

    def test_serialize_graph(self, graph):
        """Test graph serialization."""
        entity = SourceEntity(source=DataSource.MSCI, source_id="123", name="Test Entity")

        graph.add_source_entity(entity)

        # Test different formats
        ttl = graph.serialize(format="turtle")
        assert "Test Entity" in ttl

        xml = graph.serialize(format="xml")
        assert "Test Entity" in xml


class TestAdapterIntegration:
    """Integration tests for adapters with resolver."""

    def test_full_workflow(self):
        """Test complete workflow from raw data to resolution."""
        # Simulate raw data from sources
        bloomberg_data = [
            {
                "id": "BBG000B9XRY4",
                "name": "Apple Inc.",
                "isin": "US0378331005",
                "lei": "HWUPKR0MPOU8FGXBT394",
                "securityType": "EQUITY",
            }
        ]

        refinitiv_data = [
            {
                "permId": "4295905573",
                "organizationName": "Apple Inc",
                "isin": "US0378331005",
                "lei": "HWUPKR0MPOU8FGXBT394",
                "organizationType": "Corporation",
            }
        ]

        msci_data = [
            {
                "msciId": "IID000000002157615",
                "companyName": "APPLE INC",
                "isin": "US0378331005",
                "lei": "HWUPKR0MPOU8FGXBT394",
                "entityType": "COMPANY",
            }
        ]

        # Parse with adapters
        bloomberg_adapter = BloombergAdapter()
        refinitiv_adapter = RefinitivAdapter()
        msci_adapter = MSCIAdapter()

        bloomberg_entities = bloomberg_adapter.parse_entities(bloomberg_data)
        refinitiv_entities = refinitiv_adapter.parse_entities(refinitiv_data)
        msci_entities = msci_adapter.parse_entities(msci_data)

        # Resolve
        resolver = EntityResolver()
        resolver.add_entities(bloomberg_entities)
        resolver.add_entities(refinitiv_entities)
        resolver.add_entities(msci_entities)

        results = resolver.resolve()

        # All three should resolve to one entity
        assert len(results) == 1
        canonical = results[0].canonical_entity
        assert len(canonical.source_entities) == 3

        # Check identifier merging
        lei_ids = [i for i in canonical.identifiers if i.id_type == "LEI"]
        assert len(lei_ids) >= 1  # At least one LEI

        # Check sources
        assert DataSource.BLOOMBERG in canonical.sources
        assert DataSource.REFINITIV in canonical.sources
        assert DataSource.MSCI in canonical.sources
