"""
tools/__init__.py — Registers all tools onto a FastMCP instance.

Import and call register_all() to attach every tool module to the server.
Adding a new tool = create a new module + add one line here.
"""

from fastmcp import FastMCP

from . import connection, query, schema, stats


def register_all(mcp: FastMCP, get_config: callable) -> None:
    """Attach all tool modules to *mcp*."""
    connection.register(mcp, get_config)
    query.register(mcp, get_config)
    schema.register(mcp, get_config)
    stats.register(mcp, get_config)
