"""
tools/schema.py — Database schema inspection tools.

Provides:
  - list_tables   : list all user tables, optionally filtered by schema
  - describe_table: return column metadata for a given table
"""

import logging

from fastmcp import FastMCP

from ..db import get_connection, rows_to_dict

logger = logging.getLogger("sqlserver-mcp.tools.schema")


def register(mcp: FastMCP, get_config: callable) -> None:
    """Register schema inspection tools onto *mcp*."""

    @mcp.tool()
    def list_tables(schema: str | None = None) -> dict:
        """
        List all user tables in the current database.

        Args:
            schema: Optional schema name to filter by (e.g. 'dbo').
        """
        config = get_config()
        sql = """
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """
        sql_params: list = []
        if schema:
            sql += " AND TABLE_SCHEMA = ?"
            sql_params.append(schema)
        sql += " ORDER BY TABLE_SCHEMA, TABLE_NAME"

        conn = get_connection(config)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, sql_params)
            tables = rows_to_dict(cursor)
            return {"table_count": len(tables), "tables": tables}
        finally:
            conn.close()

    @mcp.tool()
    def describe_table(table: str) -> dict:
        """
        Return column names, data types, nullability, and ordinal position for a table.

        Args:
            table: Table name, optionally schema-qualified (e.g. 'dbo.Customers').
        """
        parts = table.strip().split(".", 1)
        schema, tbl = (parts[0], parts[1]) if len(parts) == 2 else ("dbo", parts[0])

        config = get_config()
        conn = get_connection(config)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    ORDINAL_POSITION
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """,
                [schema, tbl],
            )
            columns = rows_to_dict(cursor)
            if not columns:
                return {"error": f"Table '{schema}.{tbl}' not found or has no columns."}
            return {"table": f"{schema}.{tbl}", "columns": columns}
        finally:
            conn.close()
