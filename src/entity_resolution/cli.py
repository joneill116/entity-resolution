"""
Command-line interface for entity resolution.

This module provides the CLI entry point for the entity resolution package.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from entity_resolution import EntityResolver, __version__
from entity_resolution.adapters import (
    BloombergAdapter,
    BurgissAdapter,
    MSCIAdapter,
    RefinitivAdapter,
)
from entity_resolution.models import DataSource, SourceEntity
from entity_resolution.resolution.matchers import MatchConfig

# Adapter registry - maps data sources to adapter classes
ADAPTERS: dict[DataSource, type] = {
    DataSource.BLOOMBERG: BloombergAdapter,
    DataSource.REFINITIV: RefinitivAdapter,
    DataSource.MSCI: MSCIAdapter,
    DataSource.BURGISS: BurgissAdapter,
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_entities_from_file(file_path: Path, source: DataSource) -> list[SourceEntity]:
    """Load entities from a JSON file."""
    with open(file_path) as f:
        data: list[dict[str, Any]] | dict[str, Any] = json.load(f)

    if not isinstance(data, list):
        data = [data]

    adapter_class = ADAPTERS.get(source)
    if not adapter_class:
        raise ValueError(f"Unsupported source: {source}")

    adapter = adapter_class()
    result: list[SourceEntity] = adapter.parse_entities(data)
    return result


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Entity Resolution - Semantic entity matching across data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resolve entities from multiple sources
  entity-resolve --bloomberg data/bloomberg.json --refinitiv data/refinitiv.json

  # Export resolved graph
  entity-resolve --bloomberg data/bloomberg.json --output graph.ttl

  # Adjust matching threshold
  entity-resolve --bloomberg data.json --threshold 0.8
        """,
    )

    parser.add_argument("--version", action="version", version=f"entity-resolution {__version__}")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    # Source file arguments
    parser.add_argument("--bloomberg", type=Path, help="Bloomberg data file (JSON)")
    parser.add_argument("--refinitiv", type=Path, help="Refinitiv data file (JSON)")
    parser.add_argument("--msci", type=Path, help="MSCI data file (JSON)")
    parser.add_argument("--burgiss", type=Path, help="Burgiss data file (JSON)")

    # Configuration
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum similarity threshold (default: 0.7)",
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file for resolved graph (TTL format)",
    )

    parser.add_argument(
        "--format",
        choices=["turtle", "xml", "json-ld", "n3"],
        default="turtle",
        help="Output format (default: turtle)",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print resolution statistics",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Check if at least one source is provided
    sources = {
        DataSource.BLOOMBERG: args.bloomberg,
        DataSource.REFINITIV: args.refinitiv,
        DataSource.MSCI: args.msci,
        DataSource.BURGISS: args.burgiss,
    }

    active_sources = {k: v for k, v in sources.items() if v is not None}

    if not active_sources:
        parser.print_help()
        print("\nError: At least one data source file must be provided.")
        return 1

    # Configure resolver
    config = MatchConfig(min_similarity_threshold=args.threshold)
    resolver = EntityResolver(config=config)

    # Load entities from all sources
    for source, file_path in active_sources.items():
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 1

        logger.info(f"Loading entities from {source.value}: {file_path}")
        entities = load_entities_from_file(file_path, source)
        resolver.add_entities(entities)

    # Resolve entities
    logger.info("Resolving entities...")
    results = resolver.resolve()

    # Print results
    print("\nResolution Results:")
    print(f"  Source entities: {resolver.entity_count}")
    print(f"  Resolved entities: {len(results)}")
    print(f"  Matches found: {resolver.match_count}")

    # Print resolved entities
    for result in results:
        entity = result.canonical_entity
        sources_list = [s.value for s in entity.sources]
        print(f"\n  • {entity.canonical_name}")
        print(f"    Type: {entity.entity_type.value}")
        print(f"    Sources: {', '.join(sources_list)}")
        if entity.identifiers:
            ids = [f"{i.id_type}:{i.value}" for i in entity.identifiers[:3]]
            print(f"    Identifiers: {', '.join(ids)}")

    # Print statistics if requested
    if args.stats:
        stats = resolver.get_statistics()
        print("\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # Export graph if output specified
    if args.output:
        logger.info(f"Exporting graph to {args.output}")
        resolver.graph.save(args.output, format=args.format)
        print(f"\nGraph exported to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
