"""
tools/stats.py — Table statistics tools.

Provides:
  - get_row_count: fast approximate row count via system metadata
"""

import logging

from fastmcp import FastMCP

from ..db import get_connection

logger = logging.getLogger("sqlserver-mcp.tools.stats")


def register(mcp: FastMCP, get_config: callable) -> None:
    """Register statistics tools onto *mcp*."""

    @mcp.tool()
    def get_row_count(table: str) -> dict:
        """
        Return the approximate row count for a table using SQL Server system metadata.

        Args:
            table: Table name, optionally schema-qualified (e.g. 'dbo.Orders').
        """
        tbl_name = table.strip().split(".")[-1]
        config = get_config()
        conn = get_connection(config)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT SUM(p.rows) AS row_count
                FROM sys.tables t
                JOIN sys.partitions p ON t.object_id = p.object_id
                WHERE p.index_id IN (0, 1)
                  AND t.name = ?
                """,
                [tbl_name],
            )
            row = cursor.fetchone()
            count = int(row[0]) if row and row[0] is not None else 0
            return {"table": table, "row_count": count}
        finally:
            conn.close()
