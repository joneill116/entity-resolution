"""
Unit tests for data source adapters.
"""

import pytest

from entity_resolution.adapters import (
    BloombergAdapter,
    BurgissAdapter,
    MSCIAdapter,
    RefinitivAdapter,
)
from entity_resolution.models import DataSource, EntityType


class TestBloombergAdapter:
    """Tests for the Bloomberg adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return BloombergAdapter()

    def test_source_property(self, adapter):
        """Test source property returns Bloomberg."""
        assert adapter.source == DataSource.BLOOMBERG

    def test_parse_company_entity(self, adapter):
        """Test parsing a company entity."""
        raw_data = {
            "id": "BBG000B9XRY4",
            "name": "Apple Inc.",
            "shortName": "APPLE",
            "isin": "US0378331005",
            "figi": "BBG000B9XRY4",
            "ticker": "AAPL",
            "securityType": "EQUITY",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.source == DataSource.BLOOMBERG
        assert entity.source_id == "BBG000B9XRY4"
        assert entity.name == "Apple Inc."
        assert entity.entity_type == EntityType.SECURITY
        assert "APPLE" in entity.alternate_names
        assert len(entity.identifiers) >= 3

    def test_parse_fund_entity(self, adapter):
        """Test parsing a fund entity."""
        raw_data = {
            "bbgid": "BBG001234567",
            "name": "Vanguard S&P 500 ETF",
            "assetClass": "FUND",
            "isin": "US9229083632",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.entity_type == EntityType.FUND
        assert entity.source_id == "BBG001234567"

    def test_parse_multiple_entities(self, adapter):
        """Test parsing multiple entities."""
        data = [
            {"id": "1", "name": "Company A"},
            {"id": "2", "name": "Company B"},
            {"id": "3", "name": "Company C"},
        ]

        entities = adapter.parse_entities(data)

        assert len(entities) == 3
        assert all(e.source == DataSource.BLOOMBERG for e in entities)


class TestRefinitivAdapter:
    """Tests for the Refinitiv adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return RefinitivAdapter()

    def test_source_property(self, adapter):
        """Test source property returns Refinitiv."""
        assert adapter.source == DataSource.REFINITIV

    def test_parse_organization(self, adapter):
        """Test parsing an organization entity."""
        raw_data = {
            "permId": "4295905573",
            "organizationName": "Apple Inc.",
            "officialName": "Apple Inc",
            "ric": "AAPL.O",
            "lei": "HWUPKR0MPOU8FGXBT394",
            "isin": "US0378331005",
            "organizationType": "Corporation",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.source == DataSource.REFINITIV
        assert entity.source_id == "4295905573"
        assert entity.name == "Apple Inc."
        assert entity.entity_type == EntityType.COMPANY

        # Check identifiers
        id_types = {i.id_type for i in entity.identifiers}
        assert "RIC" in id_types
        assert "LEI" in id_types
        assert "ISIN" in id_types


class TestMSCIAdapter:
    """Tests for the MSCI adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return MSCIAdapter()

    def test_source_property(self, adapter):
        """Test source property returns MSCI."""
        assert adapter.source == DataSource.MSCI

    def test_parse_company_with_esg(self, adapter):
        """Test parsing a company with ESG rating."""
        raw_data = {
            "msciId": "IID000000002157615",
            "companyName": "Apple Inc",
            "isin": "US0378331005",
            "lei": "HWUPKR0MPOU8FGXBT394",
            "entityType": "COMPANY",
            "esgRating": "AA",
            "sector": "Technology",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.source == DataSource.MSCI
        assert entity.source_id == "IID000000002157615"
        assert entity.name == "Apple Inc"
        assert entity.entity_type == EntityType.COMPANY
        assert entity.attributes.get("esgRating") == "AA"


class TestBurgissAdapter:
    """Tests for the Burgiss adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return BurgissAdapter()

    def test_source_property(self, adapter):
        """Test source property returns Burgiss."""
        assert adapter.source == DataSource.BURGISS

    def test_parse_fund(self, adapter):
        """Test parsing a fund entity."""
        raw_data = {
            "fundId": "FUND12345",
            "fundName": "Blackstone Capital Partners VIII",
            "type": "FUND",
            "vintage": 2019,
            "strategy": "Buyout",
            "lei": "549300HLQLP39AWVQ753",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.source == DataSource.BURGISS
        assert entity.source_id == "FUND12345"
        assert entity.name == "Blackstone Capital Partners VIII"
        assert entity.entity_type == EntityType.FUND

    def test_parse_general_partner(self, adapter):
        """Test parsing a general partner (manager)."""
        raw_data = {
            "managerId": "MGR001",
            "managerName": "Blackstone Group Inc.",
            "type": "GP",
            "lei": "5493004TZR6D8VL7HL73",
            "legalName": "The Blackstone Group Inc.",
        }

        entity = adapter.parse_entity(raw_data)

        assert entity.source == DataSource.BURGISS
        assert entity.entity_type == EntityType.COMPANY
        assert "The Blackstone Group Inc." in entity.alternate_names


class TestBaseAdapterNormalization:
    """Tests for base adapter name normalization."""

    def test_normalize_name(self):
        """Test name normalization."""
        adapter = BloombergAdapter()

        assert adapter.normalize_name("Apple Inc.") == "APPLE"
        assert adapter.normalize_name("Microsoft Corp") == "MICROSOFT"
        assert adapter.normalize_name("  Google LLC  ") == "GOOGLE"
        assert adapter.normalize_name("") == ""
