"""
tools/query.py — SQL query execution tool (read-only).
"""

import logging

from fastmcp import FastMCP

from ..db import get_connection, rows_to_dict, validate_readonly

logger = logging.getLogger("sqlserver-mcp.tools.query")


def register(mcp: FastMCP, get_config: callable) -> None:
    """Register the execute_query tool onto *mcp*."""

    @mcp.tool()
    def execute_query(query: str, params: list | None = None) -> dict:
        """
        Execute a read-only SELECT or WITH query and return the results as JSON.

        Args:
            query:  A SELECT or WITH (CTE) SQL statement.
            params: Optional list of positional parameters for parameterised queries.
        """
        query = query.strip()
        error = validate_readonly(query)
        if error:
            return {"error": error}

        config = get_config()
        conn = get_connection(config)
        try:
            cursor = conn.cursor()
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
            cursor.execute(query, params or [])
            rows = rows_to_dict(cursor)
            return {"row_count": len(rows), "rows": rows}
        finally:
            conn.close()
