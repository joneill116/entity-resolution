"""
Burgiss data source adapter.

This module provides the adapter for parsing and normalizing
entity data from Burgiss Group (private equity/alternatives data).
"""

from typing import Any

from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.models import DataSource, EntityType, Identifier, SourceEntity


class BurgissAdapter(BaseAdapter):
    """
    Adapter for Burgiss entity data.

    Maps Burgiss-specific fields to the canonical entity model.
    Burgiss data typically includes private equity funds,
    general partners, and portfolio companies.
    """

    @property
    def source(self) -> DataSource:
        """Return Burgiss as the data source."""
        return DataSource.BURGISS

    def _detect_entity_type(self, raw_data: dict[str, Any]) -> EntityType:
        """Detect entity type from Burgiss data."""
        entity_type_field = raw_data.get("type", "").upper()
        entity_category = raw_data.get("category", "").upper()

        if entity_type_field == "FUND" or "FUND" in entity_category:
            return EntityType.FUND
        elif (
            entity_type_field in ("GP", "MANAGER", "GENERAL PARTNER")
            or entity_type_field == "PORTFOLIO COMPANY"
            or entity_category == "COMPANY"
        ):
            return EntityType.COMPANY
        elif entity_type_field == "PERSON":
            return EntityType.PERSON
        return EntityType.UNKNOWN

    def _extract_identifiers(self, raw_data: dict[str, Any]) -> list[Identifier]:
        """Extract identifiers from Burgiss data."""
        identifiers = []

        # Burgiss-specific identifiers
        id_mappings = [
            ("burgissId", "BURGISSID"),
            ("fundId", "FUNDID"),
            ("managerId", "MANAGERID"),
            ("lei", "LEI"),
            ("ein", "EIN"),  # Employer Identification Number
        ]

        for field, id_type in id_mappings:
            value = raw_data.get(field)
            if value:
                identifiers.append(
                    Identifier(source=self.source, id_type=id_type, value=str(value))
                )

        return identifiers

    def _extract_alternate_names(self, raw_data: dict[str, Any]) -> list[str]:
        """Extract alternate names from Burgiss data."""
        alt_names = []

        name_fields = ["shortName", "legalName", "dbaName", "formerName"]
        for field in name_fields:
            name = raw_data.get(field)
            if name:
                alt_names.append(name)

        # Handle list of former names
        former_names = raw_data.get("formerNames", [])
        if isinstance(former_names, list):
            alt_names.extend(former_names)

        return alt_names

    def parse_entity(self, raw_data: dict[str, Any]) -> SourceEntity:
        """
        Parse Burgiss data into a SourceEntity.

        Expected fields:
            - burgissId or fundId or managerId: Primary identifier
            - name or fundName or managerName: Primary name
            - shortName, legalName, dbaName: Alternate names
            - lei: Legal Entity Identifier
            - type, category: Type indicators
            - vintage, strategy: Fund-specific data
        """
        name = raw_data.get("name") or raw_data.get("fundName") or raw_data.get("managerName", "")

        source_id = str(
            raw_data.get("burgissId") or raw_data.get("fundId") or raw_data.get("managerId", "")
        )

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
                if k not in ("burgissId", "fundId", "managerId", "name", "fundName", "managerName")
            },
            raw_data=raw_data,
        )

    def parse_entities(self, data: list[dict[str, Any]]) -> list[SourceEntity]:
        """Parse multiple entities from Burgiss data."""
        return [self.parse_entity(item) for item in data]
