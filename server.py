"""
server.py — FastMCP server initialisation.

Responsibilities:
  - Create the FastMCP instance
  - Provide the config accessor used by all tools
  - Register all tool modules via tools.register_all()
  - Expose serve() as the single startup entry point
"""

import logging

from fastmcp import FastMCP

from .config import DatabaseConfig

logger = logging.getLogger("sqlserver-mcp.server")

mcp = FastMCP(
    name="sqlserver-mcp",
    instructions=(
        "Read-only MCP server for SQL Server. "
        "Only SELECT and WITH queries are permitted. "
        "All write operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked."
    ),
)

# Holds the active config — injected at startup via serve()
_config: DatabaseConfig | None = None


def _get_config() -> DatabaseConfig:
    if _config is None:
        raise RuntimeError("Server not initialised. Call serve() first.")
    return _config


# Register all tool modules at import time
register_all(mcp, _get_config)


def serve(config: DatabaseConfig) -> None:
    """Inject config and start the MCP server on stdio."""
    global _config
    _config = config
    logger.info(
        "SQL Server MCP server starting — %s@%s:%s",
        config.database, config.server, config.port,
    )
    mcp.run()
