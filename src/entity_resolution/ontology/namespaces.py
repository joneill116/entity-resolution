"""
Ontology namespace definitions and management.

This module provides the RDF namespace bindings and utilities
for working with the entity resolution ontology.
"""

from pathlib import Path

from rdflib import Namespace
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD

# Custom namespace for entity resolution ontology
ER = Namespace("http://entity-resolution.org/ontology#")

# FIBO namespaces (Financial Industry Business Ontology)
FIBO_FND_ORG = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/FND/Organizations/Organizations/"
)
FIBO_FND_REL = Namespace("https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/")

# Standard namespace bindings
NAMESPACE_BINDINGS = {
    "er": ER,
    "owl": OWL,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
    "skos": SKOS,
    "dcterms": DCTERMS,
    "foaf": FOAF,
    "fibo-fnd-org": FIBO_FND_ORG,
    "fibo-fnd-rel": FIBO_FND_REL,
}

# Path to ontology files
ONTOLOGY_DIR = Path(__file__).parent
MAIN_ONTOLOGY_FILE = ONTOLOGY_DIR / "entity_resolution.ttl"


def get_ontology_path() -> Path:
    """Get the path to the main ontology file."""
    return MAIN_ONTOLOGY_FILE


def bind_namespaces(graph) -> None:
    """Bind all standard namespaces to a graph."""
    for prefix, namespace in NAMESPACE_BINDINGS.items():
        graph.bind(prefix, namespace)
