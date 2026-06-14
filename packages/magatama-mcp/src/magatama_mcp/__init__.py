"""
MAGATAMA MCP - MCP Server for AI Coding Support

MAGATAMA (勾玉) provides knowledge graph context to AI coding assistants
via the Model Context Protocol (MCP).

This package depends on magatama-core (Article I compliance).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: the distribution version in pyproject.toml.
    __version__ = version("magatama")
except PackageNotFoundError:  # pragma: no cover - e.g. running from a source tree
    __version__ = "0.0.0+unknown"
