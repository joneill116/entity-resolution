"""
Knowledge Graph implementation for entity resolution.

This module provides the core RDF graph functionality for storing
and querying entities during the resolution process.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from entity_resolution.models import (
    DataSource,
    Entity,
    EntityType,
    Identifier,
    SourceEntity,
)
from entity_resolution.ontology.namespaces import ER, bind_namespaces, get_ontology_path

if TYPE_CHECKING:
    from collections.abc import Iterator


class KnowledgeGraph:
    """
    RDF Knowledge Graph for managing entity data.

    This class provides a semantic layer for storing entities, their
    identifiers, and relationships using RDF/OWL technologies.

    Attributes:
        graph: The underlying RDFLib Graph object.
    """

    # Mapping from EntityType to ontology class
    ENTITY_TYPE_MAP = {
        EntityType.COMPANY: ER.Company,
        EntityType.FUND: ER.Fund,
        EntityType.SECURITY: ER.Security,
        EntityType.PERSON: ER.Person,
        EntityType.INDEX: ER.Index,
        EntityType.LOCATION: ER.Location,
        EntityType.UNKNOWN: ER.Entity,
    }

    # Mapping from DataSource to ontology individual
    SOURCE_MAP = {
        DataSource.BLOOMBERG: ER.BloombergSource,
        DataSource.REFINITIV: ER.RefinitivSource,
        DataSource.MSCI: ER.MSCISource,
        DataSource.BURGISS: ER.BurgissSource,
    }

    def __init__(self, load_ontology: bool = True):
        """
        Initialize the knowledge graph.

        Args:
            load_ontology: Whether to load the base ontology. Default True.
        """
        self.graph = Graph()
        bind_namespaces(self.graph)

        if load_ontology:
            self._load_ontology()

    def _load_ontology(self) -> None:
        """Load the base ontology into the graph."""
        ontology_path = get_ontology_path()
        if ontology_path.exists():
            self.graph.parse(ontology_path, format="turtle")

    def _entity_uri(self, entity_id: str | UUID) -> URIRef:
        """Generate a URI for an entity."""
        return ER[f"entity/{entity_id}"]

    def _source_entity_uri(self, source: DataSource, source_id: str) -> URIRef:
        """Generate a URI for a source entity."""
        return ER[f"source/{source.value}/{source_id}"]

    def _identifier_uri(self, id_type: str, value: str) -> URIRef:
        """Generate a URI for an identifier."""
        clean_value = value.replace(" ", "_").replace("/", "_")
        return ER[f"identifier/{id_type}/{clean_value}"]

    def add_source_entity(self, entity: SourceEntity) -> URIRef:
        """
        Add a source entity to the graph.

        Args:
            entity: The source entity to add.

        Returns:
            The URI of the added entity.
        """
        uri = self._source_entity_uri(entity.source, entity.source_id)

        # Add type triples
        self.graph.add((uri, RDF.type, ER.SourceEntity))
        entity_class = self.ENTITY_TYPE_MAP.get(entity.entity_type, ER.Entity)
        self.graph.add((uri, RDF.type, entity_class))

        # Add source relationship
        if entity.source in self.SOURCE_MAP:
            self.graph.add((uri, ER.fromSource, self.SOURCE_MAP[entity.source]))

        # Add data properties
        self.graph.add((uri, ER.hasName, Literal(entity.name)))
        self.graph.add((uri, ER.hasSourceId, Literal(entity.source_id)))
        self.graph.add(
            (uri, ER.createdAt, Literal(entity.created_at.isoformat(), datatype=XSD.dateTime))
        )

        # Add alternate names
        for alt_name in entity.alternate_names:
            self.graph.add((uri, ER.hasAlternateName, Literal(alt_name)))

        # Add identifiers
        for identifier in entity.identifiers:
            id_uri = self._add_identifier(identifier)
            self.graph.add((uri, ER.hasIdentifier, id_uri))

        return uri

    def _add_identifier(self, identifier: Identifier) -> URIRef:
        """Add an identifier to the graph."""
        uri = self._identifier_uri(identifier.id_type, identifier.value)

        # Determine identifier class
        id_class_map = {
            "ISIN": ER.ISIN,
            "LEI": ER.LEI,
            "FIGI": ER.FIGI,
            "CUSIP": ER.CUSIP,
            "SEDOL": ER.SEDOL,
            "TICKER": ER.Ticker,
        }
        id_class = id_class_map.get(identifier.id_type.upper(), ER.Identifier)

        self.graph.add((uri, RDF.type, id_class))
        self.graph.add((uri, ER.hasIdentifierValue, Literal(identifier.value)))

        return uri

    def add_canonical_entity(self, entity: Entity) -> URIRef:
        """
        Add a canonical (resolved) entity to the graph.

        Args:
            entity: The canonical entity to add.

        Returns:
            The URI of the added entity.
        """
        uri = self._entity_uri(entity.id)

        # Add type triples
        self.graph.add((uri, RDF.type, ER.CanonicalEntity))
        entity_class = self.ENTITY_TYPE_MAP.get(entity.entity_type, ER.Entity)
        self.graph.add((uri, RDF.type, entity_class))

        # Add data properties
        self.graph.add((uri, ER.hasName, Literal(entity.canonical_name)))
        self.graph.add(
            (uri, ER.createdAt, Literal(entity.created_at.isoformat(), datatype=XSD.dateTime))
        )
        self.graph.add(
            (uri, ER.updatedAt, Literal(entity.updated_at.isoformat(), datatype=XSD.dateTime))
        )

        # Add alternate names
        for alt_name in entity.alternate_names:
            self.graph.add((uri, ER.hasAlternateName, Literal(alt_name)))

        # Add identifiers
        for identifier in entity.identifiers:
            id_uri = self._add_identifier(identifier)
            self.graph.add((uri, ER.hasIdentifier, id_uri))

        # Link source entities
        for source_entity in entity.source_entities:
            source_uri = self._source_entity_uri(source_entity.source, source_entity.source_id)
            self.graph.add((source_uri, ER.resolvesTo, uri))
            self.graph.add((uri, ER.hasSourceEntity, source_uri))

        return uri

    def link_entities_match(
        self, entity_a: SourceEntity, entity_b: SourceEntity, similarity: float
    ) -> None:
        """
        Record a match relationship between two source entities.

        Args:
            entity_a: First source entity.
            entity_b: Second source entity.
            similarity: The similarity score of the match.
        """
        uri_a = self._source_entity_uri(entity_a.source, entity_a.source_id)
        uri_b = self._source_entity_uri(entity_b.source, entity_b.source_id)

        self.graph.add((uri_a, ER.matchesWith, uri_b))

    def get_entities_by_identifier(self, id_type: str, value: str) -> list[URIRef]:
        """
        Find entities with a specific identifier.

        Args:
            id_type: The type of identifier (e.g., 'ISIN', 'LEI').
            value: The identifier value.

        Returns:
            List of entity URIs with this identifier.
        """
        id_uri = self._identifier_uri(id_type, value)
        query = f"""
        PREFIX er: <http://entity-resolution.org/ontology#>
        SELECT ?entity WHERE {{
            ?entity er:hasIdentifier <{id_uri}> .
        }}
        """
        results = self.graph.query(query)
        return [row[0] for row in results]  # type: ignore[index, misc]

    def get_entities_by_source(self, source: DataSource) -> Iterator[tuple[URIRef, str]]:
        """
        Get all entities from a specific source.

        Args:
            source: The data source to filter by.

        Yields:
            Tuples of (entity_uri, entity_name).
        """
        if source not in self.SOURCE_MAP:
            return

        source_uri = self.SOURCE_MAP[source]
        query = f"""
        PREFIX er: <http://entity-resolution.org/ontology#>
        SELECT ?entity ?name WHERE {{
            ?entity er:fromSource <{source_uri}> .
            ?entity er:hasName ?name .
        }}
        """
        results = self.graph.query(query)
        for row in results:
            yield row[0], str(row[1])  # type: ignore[index, misc]

    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize the graph to a string.

        Args:
            format: The serialization format (turtle, xml, json-ld, etc.)

        Returns:
            The serialized graph as a string.
        """
        return self.graph.serialize(format=format)

    def save(self, path: str | Path, format: str = "turtle") -> None:
        """
        Save the graph to a file.

        Args:
            path: Path to save the file.
            format: The serialization format.
        """
        self.graph.serialize(destination=str(path), format=format)

    def load(self, path: str | Path, format: str = "turtle") -> None:
        """
        Load additional data into the graph from a file.

        Args:
            path: Path to the file to load.
            format: The file format.
        """
        self.graph.parse(str(path), format=format)

    def __len__(self) -> int:
        """Return the number of triples in the graph."""
        return len(self.graph)
