"""
MSCI data source adapter.

This module provides the adapter for parsing and normalizing
entity data from MSCI Inc.
"""

from typing import Any

from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.models import DataSource, EntityType, Identifier, SourceEntity


class MSCIAdapter(BaseAdapter):
    """
    Adapter for MSCI entity data.

    Maps MSCI-specific fields to the canonical entity model.
    MSCI data typically includes ESG ratings, index constituents,
    and company information.
    """

    @property
    def source(self) -> DataSource:
        """Return MSCI as the data source."""
        return DataSource.MSCI

    def _detect_entity_type(self, raw_data: dict[str, Any]) -> EntityType:
        """Detect entity type from MSCI data."""
        entity_type_field = raw_data.get("entityType", "").upper()
        classification = raw_data.get("classification", "").upper()

        if entity_type_field == "INDEX" or "INDEX" in classification:
            return EntityType.INDEX
        elif entity_type_field == "FUND":
            return EntityType.FUND
        elif entity_type_field == "SECURITY":
            return EntityType.SECURITY
        elif entity_type_field == "COMPANY" or raw_data.get("issuerName"):
            return EntityType.COMPANY
        return EntityType.UNKNOWN

    def _extract_identifiers(self, raw_data: dict[str, Any]) -> list[Identifier]:
        """Extract identifiers from MSCI data."""
        identifiers = []

        # MSCI-specific identifiers
        id_mappings = [
            ("msciId", "MSCIID"),
            ("issuerIsin", "ISIN"),
            ("isin", "ISIN"),
            ("lei", "LEI"),
            ("sedol", "SEDOL"),
            ("cusip", "CUSIP"),
            ("ticker", "TICKER"),
        ]

        for field, id_type in id_mappings:
            value = raw_data.get(field)
            if value:
                identifiers.append(
                    Identifier(source=self.source, id_type=id_type, value=str(value))
                )

        return identifiers

    def _extract_alternate_names(self, raw_data: dict[str, Any]) -> list[str]:
        """Extract alternate names from MSCI data."""
        alt_names = []

        name_fields = ["issuerName", "shortName", "legalName", "tradingName"]
        for field in name_fields:
            name = raw_data.get(field)
            if name:
                alt_names.append(name)

        return alt_names

    def parse_entity(self, raw_data: dict[str, Any]) -> SourceEntity:
        """
        Parse MSCI data into a SourceEntity.

        Expected fields:
            - msciId: MSCI identifier
            - companyName or issuerName or name: Primary name
            - isin, lei, sedol: Identifiers
            - entityType, classification: Type indicators
            - esgRating: ESG rating if available
            - sector, industry, country: Classification data
        """
        name = raw_data.get("companyName") or raw_data.get("issuerName") or raw_data.get("name", "")

        source_id = str(raw_data.get("msciId") or raw_data.get("isin", ""))

        return SourceEntity(
            source=self.source,
            source_id=source_id,
            entity_type=self._detect_entity_type(raw_data),
            name=name,
            alternate_names=self._extract_alternate_names(raw_data),
            identifiers=self._extract_identifiers(raw_data),
            attributes={
                k: v
                for k, v in raw_data.items()
                if k not in ("msciId", "name", "companyName", "issuerName")
            },
            raw_data=raw_data,
        )

    def parse_entities(self, data: list[dict[str, Any]]) -> list[SourceEntity]:
        """Parse multiple entities from MSCI data."""
        return [self.parse_entity(item) for item in data]
