"""
tools/connection.py — Connection health-check tool.
"""

import logging

from fastmcp import FastMCP

from ..config import DatabaseConfig
from ..db import get_connection

logger = logging.getLogger("sqlserver-mcp.tools.connection")


def register(mcp: FastMCP, get_config: callable) -> None:
    """Register the test_connection tool onto *mcp*."""

    @mcp.tool()
    def test_connection() -> dict:
        """Verify connectivity to SQL Server and return version information."""
        config: DatabaseConfig = get_config()
        conn = get_connection(config)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION AS version, DB_NAME() AS db_name")
            row = cursor.fetchone()
            return {
                "status": "connected",
                "server": config.server,
                "port": config.port,
                "database": row[1],
                "version": row[0].split("\n")[0].strip(),
            }
        finally:
            conn.close()
