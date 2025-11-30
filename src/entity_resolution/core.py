"""
Core entity resolution engine.

This module provides the main EntityResolver class that orchestrates
the entity resolution process across multiple data sources.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from entity_resolution.graph import KnowledgeGraph
from entity_resolution.models import (
    ConfidenceLevel,
    DataSource,
    Entity,
    EntityMatch,
    EntityType,
    ResolutionResult,
    SourceEntity,
)
from entity_resolution.resolution.matchers import CompositeMatcher, MatchConfig

if TYPE_CHECKING:
    from collections.abc import Iterable


logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Main entity resolution engine.

    This class orchestrates the entire entity resolution process:
    1. Ingesting entities from multiple sources
    2. Building a knowledge graph
    3. Finding matching entities across sources
    4. Resolving matches into canonical entities

    Example:
        >>> resolver = EntityResolver()
        >>> resolver.add_entities([entity1, entity2, entity3])
        >>> results = resolver.resolve()
        >>> for result in results:
        ...     print(f"Resolved: {result.canonical_entity.canonical_name}")
    """

    def __init__(
        self,
        config: MatchConfig | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
    ):
        """
        Initialize the entity resolver.

        Args:
            config: Matching configuration. Uses defaults if not provided.
            knowledge_graph: Optional existing knowledge graph. Creates new if not provided.
        """
        self.config = config or MatchConfig()
        self.graph = knowledge_graph or KnowledgeGraph()
        self.matcher = CompositeMatcher(self.config)

        # Storage for entities pending resolution
        self._source_entities: list[SourceEntity] = []
        self._resolved_entities: list[Entity] = []
        self._matches: list[EntityMatch] = []

    def add_entity(self, entity: SourceEntity) -> None:
        """
        Add a source entity to the resolver.

        Args:
            entity: The source entity to add.
        """
        self._source_entities.append(entity)
        self.graph.add_source_entity(entity)
        logger.debug(f"Added entity: {entity.name} from {entity.source.value}")

    def add_entities(self, entities: Iterable[SourceEntity]) -> int:
        """
        Add multiple source entities to the resolver.

        Args:
            entities: Iterable of source entities.

        Returns:
            Number of entities added.
        """
        count = 0
        for entity in entities:
            self.add_entity(entity)
            count += 1
        logger.info(f"Added {count} entities for resolution")
        return count

    def find_matches(
        self, min_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    ) -> list[EntityMatch]:
        """
        Find all matching entity pairs.

        Args:
            min_confidence: Minimum confidence level for matches.

        Returns:
            List of entity matches.
        """
        matches = []
        entities = self._source_entities
        n = len(entities)

        logger.info(f"Finding matches among {n} entities...")

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                entity_a = entities[i]
                entity_b = entities[j]

                # Skip if same source (unless cross-source matching is disabled)
                # For entity resolution, we typically want cross-source matches
                if entity_a.source == entity_b.source:
                    continue

                match = self.matcher.match(entity_a, entity_b)
                if match and self._meets_confidence(match.confidence, min_confidence):
                    matches.append(match)
                    self.graph.link_entities_match(entity_a, entity_b, match.similarity_score)
                    logger.debug(
                        f"Match found: {entity_a.name} <-> {entity_b.name} "
                        f"(score: {match.similarity_score:.2%})"
                    )

        self._matches = matches
        logger.info(f"Found {len(matches)} matches")
        return matches

    def _meets_confidence(
        self, confidence: ConfidenceLevel, min_confidence: ConfidenceLevel
    ) -> bool:
        """Check if confidence meets minimum threshold."""
        levels = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1,
            ConfidenceLevel.UNCERTAIN: 0,
        }
        return levels.get(confidence, 0) >= levels.get(min_confidence, 0)

    def resolve(
        self, min_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    ) -> list[ResolutionResult]:
        """
        Resolve entities across sources.

        This method:
        1. Finds all matches between entities
        2. Groups matched entities using union-find
        3. Creates canonical entities for each group
        4. Returns resolution results

        Args:
            min_confidence: Minimum confidence level for matches.

        Returns:
            List of resolution results.
        """
        start_time = time.time()

        # Find matches if not already done
        if not self._matches:
            self.find_matches(min_confidence)

        # Build clusters of matching entities using union-find
        clusters = self._cluster_entities()

        # Create resolution results for all clusters
        results = []
        for cluster in clusters:
            result = self._create_resolution_result(cluster)
            results.append(result)

        processing_time = (time.time() - start_time) * 1000
        for result in results:
            result.processing_time_ms = processing_time / len(results) if results else 0

        logger.info(
            f"Resolution complete: {len(results)} canonical entities "
            f"from {len(self._source_entities)} source entities "
            f"in {processing_time:.2f}ms"
        )

        return results

    def _cluster_entities(self) -> list[list[SourceEntity]]:
        """
        Cluster matching entities using union-find algorithm.

        Returns:
            List of entity clusters.
        """
        # Create entity index
        entity_index = {(e.source, e.source_id): i for i, e in enumerate(self._source_entities)}

        # Union-find data structure
        n = len(self._source_entities)
        parent = list(range(n))
        rank = [0] * n

        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1

        # Union matching entities
        for match in self._matches:
            idx_a = entity_index.get((match.entity_a.source, match.entity_a.source_id))
            idx_b = entity_index.get((match.entity_b.source, match.entity_b.source_id))
            if idx_a is not None and idx_b is not None:
                union(idx_a, idx_b)

        # Group entities by cluster
        clusters: dict[int, list[SourceEntity]] = {}
        for i, entity in enumerate(self._source_entities):
            root = find(i)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(entity)

        # Return all clusters - both matched (>1 entity) and unmatched (1 entity)
        return list(clusters.values())

    def _select_canonical_name(self, cluster: list[SourceEntity]) -> str:
        """
        Select the best canonical name from a cluster of entities.

        Uses a quality-based selection that considers:
        1. Name completeness (longer names are often more formal)
        2. Source priority (some sources have higher quality data)
        3. Name frequency (more common names across sources)

        Args:
            cluster: List of source entities in the cluster.

        Returns:
            The selected canonical name.
        """
        if not cluster:
            return "Unknown"

        # Source priority - higher values are preferred
        source_priority = {
            DataSource.BLOOMBERG: 10,
            DataSource.REFINITIV: 9,
            DataSource.MSCI: 8,
            DataSource.BURGISS: 7,
            DataSource.CUSTOM: 5,
        }

        candidates: list[tuple[str, float]] = []

        for entity in cluster:
            if not entity.name:
                continue

            name = entity.name.strip()
            if not name:
                continue

            # Calculate quality score
            # Length bonus (prefer more complete names, but cap it)
            length_score = min(len(name) / 50.0, 1.0)

            # Source priority
            priority_score = source_priority.get(entity.source, 5) / 10.0

            # Penalize names that are all uppercase or contain too many abbreviations
            has_proper_case = not name.isupper() and not name.islower()
            case_score = 1.0 if has_proper_case else 0.7

            # Combined score
            quality_score = (length_score * 0.3) + (priority_score * 0.5) + (case_score * 0.2)
            candidates.append((name, quality_score))

        if not candidates:
            return "Unknown"

        # Return the name with the highest quality score
        return max(candidates, key=lambda x: x[1])[0]

    def _create_resolution_result(self, cluster: list[SourceEntity]) -> ResolutionResult:
        """Create a resolution result from a cluster of matched entities."""
        # Determine canonical name using a quality-based selection
        canonical_name = self._select_canonical_name(cluster)

        # Determine entity type
        types = [e.entity_type for e in cluster if e.entity_type != EntityType.UNKNOWN]
        entity_type = types[0] if types else EntityType.UNKNOWN

        # Create canonical entity
        canonical = Entity(
            id=uuid4(),
            entity_type=entity_type,
            canonical_name=canonical_name,
        )

        # Add all source entities
        for source_entity in cluster:
            canonical.add_source_entity(source_entity)

        # Add to graph
        self.graph.add_canonical_entity(canonical)
        self._resolved_entities.append(canonical)

        # Find matches within this cluster
        cluster_matches = [
            m
            for m in self._matches
            if any(
                (m.entity_a.source == e.source and m.entity_a.source_id == e.source_id)
                or (m.entity_b.source == e.source and m.entity_b.source_id == e.source_id)
                for e in cluster
            )
        ]

        return ResolutionResult(
            canonical_entity=canonical,
            matched_entities=cluster_matches,
            unresolved_entities=[],
        )

    def get_entity_by_identifier(self, id_type: str, value: str) -> Entity | None:
        """
        Look up a resolved entity by identifier.

        Args:
            id_type: Type of identifier (e.g., 'LEI', 'ISIN').
            value: The identifier value.

        Returns:
            The resolved entity if found, None otherwise.
        """
        for entity in self._resolved_entities:
            for identifier in entity.identifiers:
                if identifier.id_type.upper() == id_type.upper() and identifier.value == value:
                    return entity
        return None

    def export_graph(self, format: str = "turtle") -> str:
        """
        Export the knowledge graph.

        Args:
            format: Serialization format (turtle, xml, json-ld).

        Returns:
            Serialized graph as string.
        """
        return self.graph.serialize(format=format)

    @property
    def entity_count(self) -> int:
        """Get the number of source entities."""
        return len(self._source_entities)

    @property
    def resolved_count(self) -> int:
        """Get the number of resolved canonical entities."""
        return len(self._resolved_entities)

    @property
    def match_count(self) -> int:
        """Get the number of entity matches."""
        return len(self._matches)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get resolution statistics.

        Returns:
            Dictionary with resolution statistics.
        """
        sources: dict[str, int] = {}
        for entity in self._source_entities:
            source_name = entity.source.value
            sources[source_name] = sources.get(source_name, 0) + 1

        return {
            "source_entities": len(self._source_entities),
            "resolved_entities": len(self._resolved_entities),
            "matches_found": len(self._matches),
            "entities_by_source": sources,
            "graph_triples": len(self.graph),
        }
