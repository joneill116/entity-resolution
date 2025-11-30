# Entity Resolution

A professional-grade Python package for entity resolution using RDF/semantic technologies. This package enables you to map entities from multiple financial data sources (Bloomberg, Refinitiv, MSCI, Burgiss) to a semantic model and resolve them to canonical entities.

## Features

- **RDF/Semantic Foundation**: Built on RDFLib with a well-defined ontology for financial entities
- **Multi-Source Integration**: Adapters for Bloomberg, Refinitiv, MSCI, and Burgiss data sources
- **Flexible Matching**: Composite matching using identifiers (LEI, ISIN, FIGI, etc.) and fuzzy name matching
- **Knowledge Graph**: Stores entities and relationships in an RDF graph with SPARQL query support
- **Extensible Architecture**: Easy to add new data sources and matching strategies
- **Type-Safe Models**: Pydantic models for strong typing and validation

## Installation

```bash
pip install entity-resolution
```

Or install from source:

```bash
git clone https://github.com/joneill116/entity-resolution.git
cd entity-resolution
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from entity_resolution import EntityResolver
from entity_resolution.adapters import BloombergAdapter, RefinitivAdapter
from entity_resolution.models import DataSource, Identifier, SourceEntity

# Create resolver
resolver = EntityResolver()

# Create entities from different sources
bloomberg_entity = SourceEntity(
    source=DataSource.BLOOMBERG,
    source_id="BBG000B9XRY4",
    name="Apple Inc.",
    identifiers=[
        Identifier(source=DataSource.BLOOMBERG, id_type="LEI", value="HWUPKR0MPOU8FGXBT394"),
        Identifier(source=DataSource.BLOOMBERG, id_type="ISIN", value="US0378331005"),
    ]
)

refinitiv_entity = SourceEntity(
    source=DataSource.REFINITIV,
    source_id="4295905573",
    name="Apple Inc",
    identifiers=[
        Identifier(source=DataSource.REFINITIV, id_type="LEI", value="HWUPKR0MPOU8FGXBT394"),
    ]
)

# Add entities and resolve
resolver.add_entities([bloomberg_entity, refinitiv_entity])
results = resolver.resolve()

# Access resolved entities
for result in results:
    entity = result.canonical_entity
    print(f"Canonical: {entity.canonical_name}")
    print(f"Sources: {[s.value for s in entity.sources]}")
    print(f"Identifiers: {[(i.id_type, i.value) for i in entity.identifiers]}")
```

### Using Adapters

```python
from entity_resolution.adapters import BloombergAdapter, RefinitivAdapter, MSCIAdapter

# Parse raw data from sources
bloomberg_adapter = BloombergAdapter()
bloomberg_data = [
    {
        "id": "BBG000B9XRY4",
        "name": "Apple Inc.",
        "isin": "US0378331005",
        "lei": "HWUPKR0MPOU8FGXBT394",
    }
]
entities = bloomberg_adapter.parse_entities(bloomberg_data)

# Add to resolver
resolver.add_entities(entities)
```

### Command Line Interface

```bash
# Resolve entities from multiple sources
entity-resolve --bloomberg data/bloomberg.json --refinitiv data/refinitiv.json

# Export the knowledge graph
entity-resolve --bloomberg data/bloomberg.json --output graph.ttl

# Adjust matching threshold
entity-resolve --bloomberg data.json --threshold 0.8 --stats
```

## Architecture

### Package Structure

```
src/entity_resolution/
├── __init__.py          # Package exports
├── core.py              # EntityResolver main class
├── models.py            # Pydantic data models
├── cli.py               # Command-line interface
├── adapters/            # Data source adapters
│   ├── base.py          # Abstract adapter interface
│   ├── bloomberg.py     # Bloomberg adapter
│   ├── refinitiv.py     # Refinitiv adapter
│   ├── msci.py          # MSCI adapter
│   └── burgiss.py       # Burgiss adapter
├── ontology/            # RDF ontology
│   ├── namespaces.py    # Namespace definitions
│   └── entity_resolution.ttl  # OWL ontology
├── graph/               # Knowledge graph
│   └── knowledge_graph.py
└── resolution/          # Matching algorithms
    └── matchers.py      # Similarity matchers
```

### Data Model

The package uses a hierarchy of entity representations:

1. **SourceEntity**: Raw entity from a data source
2. **Entity**: Canonical resolved entity
3. **EntityMatch**: Match between two source entities
4. **ResolutionResult**: Complete resolution output

### Ontology

The semantic model is defined in OWL/Turtle format at `ontology/entity_resolution.ttl` and includes:

- **Entity Types**: Company, Fund, Security, Person, Index, Location
- **Identifiers**: LEI, ISIN, FIGI, CUSIP, SEDOL, Ticker
- **Data Sources**: Bloomberg, Refinitiv, MSCI, Burgiss
- **Relationships**: resolvesTo, matchesWith, hasIdentifier

### Matching Strategy

The composite matcher uses:

1. **Identifier Matching**: LEI (100%), ISIN (95%), FIGI (90%), CUSIP (85%), SEDOL (85%), Ticker (60%)
2. **Name Matching**: Fuzzy matching with normalization (removes suffixes like Inc., Ltd., Corp.)
3. **Weighted Combination**: Identifier matches take precedence; name similarity provides additional confidence

## Configuration

```python
from entity_resolution.resolution.matchers import MatchConfig

config = MatchConfig(
    min_similarity_threshold=0.7,     # Minimum score to consider a match
    identifier_match_weight=0.4,       # Weight for identifier matching
    name_match_weight=0.35,            # Weight for name matching
    high_confidence_threshold=0.9,     # Threshold for high confidence
    medium_confidence_threshold=0.75,  # Threshold for medium confidence
)

resolver = EntityResolver(config=config)
```

## Extending

### Adding a New Data Source

```python
from entity_resolution.adapters.base import BaseAdapter
from entity_resolution.models import DataSource, SourceEntity

class CustomAdapter(BaseAdapter):
    @property
    def source(self) -> DataSource:
        return DataSource.CUSTOM
    
    def parse_entity(self, raw_data: dict) -> SourceEntity:
        return SourceEntity(
            source=self.source,
            source_id=raw_data["id"],
            name=raw_data["name"],
            # ... map other fields
        )
    
    def parse_entities(self, data: list) -> list[SourceEntity]:
        return [self.parse_entity(item) for item in data]
```

### Custom Matcher

```python
from entity_resolution.resolution.matchers import BaseMatcher

class CustomMatcher(BaseMatcher):
    def compute_similarity(self, entity_a, entity_b):
        # Custom matching logic
        score = ...
        return score, {"custom": score}, ["Custom match reason"]
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
black --check src tests
mypy src

# Format code
black src tests
ruff check --fix src tests
```

## License

MIT License

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.