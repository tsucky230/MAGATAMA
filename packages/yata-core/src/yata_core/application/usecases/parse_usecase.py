"""Parse use cases for extracting entities from source files.

This module provides use cases for parsing source code files and
storing the extracted entities in a knowledge graph.
"""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Protocol, Sequence
import fnmatch

from yata_core.domain.entities import Entity, Relationship, RelationshipType
from yata_core.domain.repositories import KnowledgeGraphRepository
from yata_core.infrastructure.parsers.parse_result import ParseResult as ParserResult


class Parser(Protocol):
    """Protocol for language parsers."""

    def parse_file(self, file_path: Path) -> ParserResult:
        """Parse a source file and extract entities."""
        ...


@dataclass
class ParseResult:
    """Result of a parse operation."""

    success: bool
    entities_count: int = 0
    relationships_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class DirectoryParseResult:
    """Result of parsing a directory."""

    success: bool
    files_processed: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    errors: list[str] = field(default_factory=list)
    file_results: list[ParseResult] = field(default_factory=list)


class ParseFileUseCase:
    """Use case for parsing a single source file.

    This use case coordinates between a parser and the knowledge graph
    to extract entities from a source file and store them.
    """

    def __init__(
        self,
        parsers: dict[str, Parser],
        knowledge_graph: KnowledgeGraphRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            parsers: Mapping of file extensions to parsers (e.g., {".py": PythonParser()})
            knowledge_graph: The knowledge graph to store entities in
        """
        self._parsers = parsers
        self._knowledge_graph = knowledge_graph

    def execute(self, file_path: Path) -> ParseResult:
        """Parse a file and store entities in the knowledge graph.

        Args:
            file_path: Path to the source file to parse

        Returns:
            ParseResult with success status and counts
        """
        # Validate file exists
        if not file_path.exists():
            return ParseResult(
                success=False,
                errors=[f"File not found: {file_path}"],
            )

        # Get parser for file type
        suffix = file_path.suffix.lower()
        parser = self._parsers.get(suffix)
        if parser is None:
            return ParseResult(
                success=False,
                errors=[f"Unsupported file type: {suffix}"],
            )

        # Parse the file
        try:
            parse_result = parser.parse_file(file_path)
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"Parse error: {str(e)}"],
            )

        # Store entities in knowledge graph
        entities_added = 0
        for entity in parse_result.entities:
            try:
                self._knowledge_graph.entities.add(entity)
                entities_added += 1
            except ValueError:
                # Entity already exists, skip
                pass

        # Store relationships in knowledge graph
        relationships_added = 0
        for relationship in parse_result.relationships:
            try:
                self._knowledge_graph.relationships.add(relationship)
                relationships_added += 1
            except ValueError:
                # Relationship already exists, skip
                pass

        return ParseResult(
            success=True,
            entities_count=entities_added,
            relationships_count=relationships_added,
            errors=parse_result.errors,
        )


class ParseDirectoryUseCase:
    """Use case for parsing all files in a directory.

    This use case walks a directory tree and parses all matching files,
    storing the extracted entities in a knowledge graph.
    """

    def __init__(self, parse_file_usecase: ParseFileUseCase) -> None:
        """Initialize the use case.

        Args:
            parse_file_usecase: The file parsing use case to delegate to
        """
        self._parse_file = parse_file_usecase

    def execute(
        self,
        directory: Path,
        patterns: Sequence[str] | None = None,
        exclude_patterns: Sequence[str] | None = None,
    ) -> DirectoryParseResult:
        """Parse all matching files in a directory.

        Args:
            directory: Path to the directory to parse
            patterns: Glob patterns for files to include (default: ["**/*.py"])
            exclude_patterns: Glob patterns for files to exclude

        Returns:
            DirectoryParseResult with aggregate statistics
        """
        # Validate directory exists
        if not directory.exists():
            return DirectoryParseResult(
                success=False,
                errors=[f"Directory not found: {directory}"],
            )

        if not directory.is_dir():
            return DirectoryParseResult(
                success=False,
                errors=[f"Not a directory: {directory}"],
            )

        # Default patterns
        if patterns is None:
            patterns = ["**/*.py"]
        if exclude_patterns is None:
            exclude_patterns = []

        # Find all matching files
        files_to_parse: list[Path] = []
        for pattern in patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    # Check exclude patterns
                    relative_path = str(file_path.relative_to(directory))
                    excluded = any(
                        fnmatch.fnmatch(relative_path, exc_pattern)
                        or fnmatch.fnmatch(file_path.name, exc_pattern)
                        for exc_pattern in exclude_patterns
                    )
                    if not excluded and file_path not in files_to_parse:
                        files_to_parse.append(file_path)

        # Parse each file
        file_results: list[ParseResult] = []
        total_entities = 0
        total_relationships = 0
        all_errors: list[str] = []

        for file_path in files_to_parse:
            result = self._parse_file.execute(file_path)
            file_results.append(result)
            total_entities += result.entities_count
            total_relationships += result.relationships_count
            all_errors.extend(result.errors)

        return DirectoryParseResult(
            success=True,
            files_processed=len(files_to_parse),
            total_entities=total_entities,
            total_relationships=total_relationships,
            errors=all_errors,
            file_results=file_results,
        )


@dataclass
class IncrementalParseResult:
    """Result of an incremental parse operation."""

    success: bool
    files_processed: int = 0
    files_skipped: int = 0
    files_removed: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    entities_removed: int = 0
    errors: list[str] = field(default_factory=list)
    file_results: list[ParseResult] = field(default_factory=list)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents.

    Args:
        file_path: Path to the file

    Returns:
        Hex string of SHA-256 hash
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class IncrementalParseUseCase:
    """Use case for incremental parsing of source files.

    This use case tracks file changes using content hashes and only
    re-parses files that have been modified. Deleted files are
    automatically removed from the knowledge graph.
    """

    def __init__(
        self,
        parsers: dict[str, Parser],
        knowledge_graph: KnowledgeGraphRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            parsers: Mapping of file extensions to parsers
            knowledge_graph: The knowledge graph to store entities in
        """
        self._parsers = parsers
        self._knowledge_graph = knowledge_graph

    def _parse_and_store(self, file_path: Path) -> ParseResult:
        """Parse a file and store entities in the knowledge graph.

        Args:
            file_path: Path to the source file to parse

        Returns:
            ParseResult with success status and counts
        """
        # Get parser for file type
        suffix = file_path.suffix.lower()
        parser = self._parsers.get(suffix)
        if parser is None:
            return ParseResult(
                success=False,
                errors=[f"Unsupported file type: {suffix}"],
            )

        # Parse the file
        try:
            parse_result = parser.parse_file(file_path)
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"Parse error: {str(e)}"],
            )

        # Store entities in knowledge graph
        entities_added = 0
        for entity in parse_result.entities:
            try:
                self._knowledge_graph.entities.add(entity)
                entities_added += 1
            except ValueError:
                # Entity already exists, skip
                pass

        # Store relationships in knowledge graph
        relationships_added = 0
        for relationship in parse_result.relationships:
            try:
                self._knowledge_graph.relationships.add(relationship)
                relationships_added += 1
            except ValueError:
                # Relationship already exists, skip
                pass

        return ParseResult(
            success=True,
            entities_count=entities_added,
            relationships_count=relationships_added,
            errors=parse_result.errors,
        )

    def execute(
        self,
        directory: Path,
        patterns: Sequence[str] | None = None,
        exclude_patterns: Sequence[str] | None = None,
    ) -> IncrementalParseResult:
        """Incrementally parse files in a directory.

        Only files that have changed since the last parse are re-processed.
        Files that no longer exist are removed from the knowledge graph.

        Args:
            directory: Path to the directory to parse
            patterns: Glob patterns for files to include (default: ["**/*.py"])
            exclude_patterns: Glob patterns for files to exclude

        Returns:
            IncrementalParseResult with statistics
        """
        # Validate directory exists
        if not directory.exists():
            return IncrementalParseResult(
                success=False,
                errors=[f"Directory not found: {directory}"],
            )

        if not directory.is_dir():
            return IncrementalParseResult(
                success=False,
                errors=[f"Not a directory: {directory}"],
            )

        # Default patterns
        if patterns is None:
            patterns = ["**/*.py"]
        if exclude_patterns is None:
            exclude_patterns = []

        # Find all matching files
        current_files: set[str] = set()
        files_to_check: list[Path] = []

        for pattern in patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    # Check exclude patterns
                    relative_path = str(file_path.relative_to(directory))
                    excluded = any(
                        fnmatch.fnmatch(relative_path, exc_pattern)
                        or fnmatch.fnmatch(file_path.name, exc_pattern)
                        for exc_pattern in exclude_patterns
                    )
                    if not excluded:
                        file_str = str(file_path)
                        if file_str not in current_files:
                            current_files.add(file_str)
                            files_to_check.append(file_path)

        # Get previously tracked files
        tracked_files = set(self._knowledge_graph.get_tracked_files())

        # Find deleted files
        deleted_files = tracked_files - current_files

        # Remove deleted files from knowledge graph
        entities_removed = 0
        files_removed = 0
        for deleted_file in deleted_files:
            removed = self._knowledge_graph.remove_file(deleted_file)
            entities_removed += removed
            files_removed += 1

        # Process current files
        file_results: list[ParseResult] = []
        total_entities = 0
        total_relationships = 0
        all_errors: list[str] = []
        files_processed = 0
        files_skipped = 0

        for file_path in files_to_check:
            file_str = str(file_path)

            # Compute current hash
            try:
                current_hash = _compute_file_hash(file_path)
            except OSError as e:
                all_errors.append(f"Error reading {file_path}: {e}")
                continue

            # Check if file has changed
            stored_hash = self._knowledge_graph.get_file_hash(file_str)
            if stored_hash == current_hash:
                # File unchanged, skip
                files_skipped += 1
                continue

            # File is new or changed - remove old data if exists
            if stored_hash is not None:
                self._knowledge_graph.remove_file(file_str)

            # Parse the file
            result = self._parse_and_store(file_path)
            file_results.append(result)
            total_entities += result.entities_count
            total_relationships += result.relationships_count
            all_errors.extend(result.errors)
            files_processed += 1

            # Update stored hash
            self._knowledge_graph.set_file_hash(file_str, current_hash)

        return IncrementalParseResult(
            success=True,
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_removed=files_removed,
            total_entities=total_entities,
            total_relationships=total_relationships,
            entities_removed=entities_removed,
            errors=all_errors,
            file_results=file_results,
        )

