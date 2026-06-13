"""
MCP Server - Model Context Protocol implementation.

ADR-002: MCP Python SDK
REQ-MCP-001: MCP protocol compliance
"""

from magatama_mcp.server.mcp_server import MagatamaMcpServer, Resource, Tool
from magatama_mcp.server.protocol import create_mcp_server, run_stdio_server

__all__ = [
    "MagatamaMcpServer",
    "Resource",
    "Tool",
    "create_mcp_server",
    "run_stdio_server",
]
