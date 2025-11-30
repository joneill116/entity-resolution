"""
Bloomberg data source adapter.

This module provides the adapter for parsing and normalizing
entity data from Bloomberg.
"""

from typing import Any

from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.models import DataSource, EntityType, Identifier, SourceEntity


class BloombergAdapter(BaseAdapter):
    """
    Adapter for Bloomberg entity data.

    Maps Bloomberg-specific fields to the canonical entity model.
    """

    @property
    def source(self) -> DataSource:
        """Return Bloomberg as the data source."""
        return DataSource.BLOOMBERG

    def _detect_entity_type(self, raw_data: dict[str, Any]) -> EntityType:
        """Detect entity type from Bloomberg data."""
        security_type = raw_data.get("securityType", "").upper()
        asset_class = raw_data.get("assetClass", "").upper()

        if security_type in ("EQUITY", "BOND", "OPTION", "FUTURE"):
            return EntityType.SECURITY
        elif asset_class == "FUND" or "FUND" in security_type:
            return EntityType.FUND
        elif security_type == "INDEX":
            return EntityType.INDEX
        elif raw_data.get("issuer") or raw_data.get("companyName"):
            return EntityType.COMPANY
        return EntityType.UNKNOWN

    def _extract_identifiers(self, raw_data: dict[str, Any]) -> list[Identifier]:
        """Extract identifiers from Bloomberg data."""
        identifiers = []

        # Bloomberg-specific identifiers
        id_mappings = [
            ("figi", "FIGI"),
            ("isin", "ISIN"),
            ("cusip", "CUSIP"),
            ("sedol", "SEDOL"),
            ("ticker", "TICKER"),
            ("bbgid", "BBGID"),
            ("lei", "LEI"),
        ]

        for field, id_type in id_mappings:
            value = raw_data.get(field)
            if value:
                identifiers.append(
                    Identifier(source=self.source, id_type=id_type, value=str(value))
                )

        return identifiers

    def _extract_alternate_names(self, raw_data: dict[str, Any]) -> list[str]:
        """Extract alternate names from Bloomberg data."""
        alt_names = []

        # Check various name fields
        name_fields = ["shortName", "longName", "legalName", "tradingName"]
        for field in name_fields:
            name = raw_data.get(field)
            if name:
                alt_names.append(name)

        return alt_names

    def parse_entity(self, raw_data: dict[str, Any]) -> SourceEntity:
        """
        Parse Bloomberg data into a SourceEntity.

        Expected fields:
            - id or bbgid: Bloomberg identifier
            - name or companyName: Primary name
            - shortName, longName, legalName: Alternate names
            - figi, isin, cusip, sedol, ticker: Identifiers
            - securityType, assetClass: Type indicators
        """
        # Determine primary name
        name = raw_data.get("name") or raw_data.get("companyName") or raw_data.get("longName", "")

        # Determine source ID
        source_id = str(raw_data.get("id") or raw_data.get("bbgid") or raw_data.get("figi", ""))

        return SourceEntity(
            source=self.source,
            source_id=source_id,
            entity_type=self._detect_entity_type(raw_data),
            name=name,
            alternate_names=self._extract_alternate_names(raw_data),
            identifiers=self._extract_identifiers(raw_data),
            attributes={
                k: v for k, v in raw_data.items() if k not in ("id", "bbgid", "name", "companyName")
            },
            raw_data=raw_data,
        )

    def parse_entities(self, data: list[dict[str, Any]]) -> list[SourceEntity]:
        """Parse multiple entities from Bloomberg data."""
        return [self.parse_entity(item) for item in data]
