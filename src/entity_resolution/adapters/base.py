"""
Base adapter class for data source integration.

This module defines the abstract interface that all data source
adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from entity_resolution.models import DataSource, SourceEntity


class BaseAdapter(ABC):
    """
    Abstract base class for data source adapters.

    Each data source (Bloomberg, Refinitiv, MSCI, Burgiss) must implement
    this interface to integrate with the entity resolution system.
    """

    @property
    @abstractmethod
    def source(self) -> DataSource:
        """Return the data source this adapter handles."""
        pass

    @abstractmethod
    def parse_entity(self, raw_data: dict[str, Any]) -> SourceEntity:
        """
        Parse raw data from the source into a SourceEntity.

        Args:
            raw_data: Dictionary containing the raw entity data.

        Returns:
            A SourceEntity object with mapped attributes.
        """
        pass

    @abstractmethod
    def parse_entities(self, data: list[dict[str, Any]]) -> list[SourceEntity]:
        """
        Parse multiple entities from raw data.

        Args:
            data: List of raw entity dictionaries.

        Returns:
            List of SourceEntity objects.
        """
        pass

    def normalize_name(self, name: str) -> str:
        """
        Normalize an entity name for comparison.

        Args:
            name: The raw name string.

        Returns:
            Normalized name string.
        """
        if not name:
            return ""
        # Basic normalization: uppercase, strip whitespace
        normalized = name.upper().strip()
        # Remove common suffixes
        suffixes = [" INC", " INC.", " LLC", " LTD", " LTD.", " CORP", " CORP."]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
        return normalized
