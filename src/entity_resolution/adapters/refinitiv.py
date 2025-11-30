"""
Refinitiv data source adapter.

This module provides the adapter for parsing and normalizing
entity data from Refinitiv (formerly Thomson Reuters).
"""

from typing import Any

from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.models import DataSource, EntityType, Identifier, SourceEntity


class RefinitivAdapter(BaseAdapter):
    """
    Adapter for Refinitiv entity data.

    Maps Refinitiv-specific fields to the canonical entity model.
    """

    @property
    def source(self) -> DataSource:
        """Return Refinitiv as the data source."""
        return DataSource.REFINITIV

    def _detect_entity_type(self, raw_data: dict[str, Any]) -> EntityType:
        """Detect entity type from Refinitiv data."""
        instrument_type = raw_data.get("instrumentType", "").upper()
        org_type = raw_data.get("organizationType", "").upper()

        if instrument_type in ("EQUITY", "BOND", "DERIVATIVE"):
            return EntityType.SECURITY
        elif "FUND" in instrument_type or "FUND" in org_type:
            return EntityType.FUND
        elif instrument_type == "INDEX":
            return EntityType.INDEX
        elif org_type or raw_data.get("orgId"):
            return EntityType.COMPANY
        return EntityType.UNKNOWN

    def _extract_identifiers(self, raw_data: dict[str, Any]) -> list[Identifier]:
        """Extract identifiers from Refinitiv data."""
        identifiers = []

        # Refinitiv-specific identifiers
        id_mappings = [
            ("ric", "RIC"),  # Reuters Instrument Code
            ("permId", "PERMID"),  # Permanent Identifier
            ("isin", "ISIN"),
            ("cusip", "CUSIP"),
            ("sedol", "SEDOL"),
            ("lei", "LEI"),
            ("ticker", "TICKER"),
            ("orgId", "ORGID"),
        ]

        for field, id_type in id_mappings:
            value = raw_data.get(field)
            if value:
                identifiers.append(
                    Identifier(source=self.source, id_type=id_type, value=str(value))
                )

        return identifiers

    def _extract_alternate_names(self, raw_data: dict[str, Any]) -> list[str]:
        """Extract alternate names from Refinitiv data."""
        alt_names = []

        name_fields = ["officialName", "tradingName", "shortName", "localName"]
        for field in name_fields:
            name = raw_data.get(field)
            if name:
                alt_names.append(name)

        return alt_names

    def parse_entity(self, raw_data: dict[str, Any]) -> SourceEntity:
        """
        Parse Refinitiv data into a SourceEntity.

        Expected fields:
            - permId or orgId or ric: Primary identifier
            - organizationName or name: Primary name
            - officialName, tradingName, shortName: Alternate names
            - isin, cusip, sedol, lei, ric: Identifiers
            - instrumentType, organizationType: Type indicators
        """
        name = (
            raw_data.get("organizationName")
            or raw_data.get("name")
            or raw_data.get("officialName", "")
        )

        source_id = str(raw_data.get("permId") or raw_data.get("orgId") or raw_data.get("ric", ""))

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
                if k not in ("permId", "orgId", "name", "organizationName")
            },
            raw_data=raw_data,
        )

    def parse_entities(self, data: list[dict[str, Any]]) -> list[SourceEntity]:
        """Parse multiple entities from Refinitiv data."""
        return [self.parse_entity(item) for item in data]
