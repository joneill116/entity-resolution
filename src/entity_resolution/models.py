"""
Pydantic data models for entity resolution.

These models define the core data structures used throughout the package
for representing entities, their attributes, and resolution matches.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Get current UTC datetime in a timezone-aware manner."""
    return datetime.now(timezone.utc)


class DataSource(str, Enum):
    """Enumeration of supported data sources."""

    BLOOMBERG = "bloomberg"
    REFINITIV = "refinitiv"
    MSCI = "msci"
    BURGISS = "burgiss"
    CUSTOM = "custom"


class EntityType(str, Enum):
    """Types of entities that can be resolved."""

    COMPANY = "company"
    FUND = "fund"
    SECURITY = "security"
    PERSON = "person"
    LOCATION = "location"
    INDEX = "index"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence levels for entity matches."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class Identifier(BaseModel):
    """Represents an identifier for an entity from a specific source."""

    model_config = ConfigDict(frozen=True)

    source: DataSource
    id_type: str = Field(..., description="Type of identifier (e.g., ISIN, LEI, FIGI)")
    value: str = Field(..., description="The identifier value")

    def __hash__(self) -> int:
        return hash((self.source, self.id_type, self.value))


class EntityAttribute(BaseModel):
    """An attribute of an entity with provenance tracking."""

    name: str = Field(..., description="Attribute name")
    value: Any = Field(..., description="Attribute value")
    source: DataSource = Field(..., description="Source of this attribute")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


class SourceEntity(BaseModel):
    """
    Represents an entity as it appears in a source system.

    This is the raw entity data before it's mapped to the canonical model.
    """

    model_config = ConfigDict(validate_assignment=True)

    source: DataSource = Field(..., description="The data source this entity comes from")
    source_id: str = Field(..., description="The unique ID in the source system")
    entity_type: EntityType = Field(default=EntityType.UNKNOWN)
    name: str = Field(..., description="The primary name of the entity")
    alternate_names: list[str] = Field(default_factory=list)
    identifiers: list[Identifier] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def all_names(self) -> list[str]:
        """Get all names including primary and alternates."""
        return [self.name, *self.alternate_names]


class Entity(BaseModel):
    """
    Canonical entity representation in the knowledge graph.

    This is the unified entity after resolution, containing merged
    information from multiple sources.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: UUID = Field(default_factory=uuid4, description="Canonical entity ID")
    entity_type: EntityType = Field(default=EntityType.UNKNOWN)
    canonical_name: str = Field(..., description="The primary canonical name")
    alternate_names: list[str] = Field(default_factory=list)
    identifiers: list[Identifier] = Field(default_factory=list)
    attributes: list[EntityAttribute] = Field(default_factory=list)
    source_entities: list[SourceEntity] = Field(
        default_factory=list, description="Source entities that resolved to this entity"
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def sources(self) -> set[DataSource]:
        """Get all data sources that contributed to this entity."""
        return {se.source for se in self.source_entities}

    def add_source_entity(self, source_entity: SourceEntity) -> None:
        """Add a source entity and merge its information."""
        self.source_entities.append(source_entity)
        # Merge alternate names
        for name in source_entity.all_names:
            if name not in self.alternate_names and name != self.canonical_name:
                self.alternate_names.append(name)
        # Merge identifiers
        existing_ids = set(self.identifiers)
        for identifier in source_entity.identifiers:
            if identifier not in existing_ids:
                self.identifiers.append(identifier)
        self.updated_at = utc_now()


class EntityMatch(BaseModel):
    """
    Represents a potential match between two entities.

    Used during the resolution process to track candidate matches
    and their similarity scores.
    """

    model_config = ConfigDict(validate_assignment=True)

    entity_a: SourceEntity = Field(..., description="First entity in the match pair")
    entity_b: SourceEntity = Field(..., description="Second entity in the match pair")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Overall similarity score")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.UNCERTAIN)
    match_reasons: list[str] = Field(
        default_factory=list, description="Reasons why these entities match"
    )
    component_scores: dict[str, float] = Field(
        default_factory=dict, description="Individual component similarity scores"
    )
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence match."""
        return self.confidence == ConfidenceLevel.HIGH or self.similarity_score >= 0.9


class ResolutionResult(BaseModel):
    """Result of an entity resolution operation."""

    model_config = ConfigDict(validate_assignment=True)

    canonical_entity: Entity = Field(..., description="The resolved canonical entity")
    matched_entities: list[EntityMatch] = Field(
        default_factory=list, description="All matches that led to this resolution"
    )
    unresolved_entities: list[SourceEntity] = Field(
        default_factory=list, description="Entities that couldn't be resolved"
    )
    resolution_timestamp: datetime = Field(default_factory=utc_now)
    processing_time_ms: float = Field(default=0.0)
