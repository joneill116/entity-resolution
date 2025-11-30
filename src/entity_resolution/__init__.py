"""
Entity Resolution Package

A professional-grade RDF/semantic technology package for entity resolution
across financial data sources like Bloomberg, Refinitiv, MSCI, and Burgiss.
"""

from entity_resolution.core import EntityResolver
from entity_resolution.graph import KnowledgeGraph
from entity_resolution.models import Entity, EntityMatch, SourceEntity

__version__ = "0.1.0"

__all__ = [
    "EntityResolver",
    "KnowledgeGraph",
    "Entity",
    "EntityMatch",
    "SourceEntity",
    "__version__",
]
