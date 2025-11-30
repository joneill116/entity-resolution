"""
Data source adapters for entity resolution.

This module provides adapters for integrating with various
financial data sources.
"""

from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.adapters.bloomberg import BloombergAdapter
from entity_resolution.adapters.burgiss import BurgissAdapter
from entity_resolution.adapters.msci import MSCIAdapter
from entity_resolution.adapters.refinitiv import RefinitivAdapter

__all__ = [
    "BaseAdapter",
    "BloombergAdapter",
    "BurgissAdapter",
    "MSCIAdapter",
    "RefinitivAdapter",
]
