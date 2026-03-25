"""
handlers.py — Business logic for each MCP tool.
Each handler receives a DatabaseConfig and the raw arguments dict,
and returns a (data | error) dict ready to be serialised.
"""

import logging

import pyodbc

from .config import DatabaseConfig
from .database import get_connection, rows_to_dict, validate_readonly

logger = logging.getLogger("sqlserver-mcp.handlers")


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(data: dict) -> dict:
    return {"ok": True, **data}


def _err(message: str) -> dict:
    return {"ok": False, "error": message}


# ── tool handlers ─────────────────────────────────────────────────────────────

async def handle_test_connection(config: DatabaseConfig) -> dict:
    """Ping SQL Server and return version info."""
    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION AS version, DB_NAME() AS db_name")
        row = cursor.fetchone()
        return _ok({
            "status": "connected",
            "server": config.server,
            "port": config.port,
            "database": row[1],
            "version": row[0].split("\n")[0].strip(),
        })
    finally:
        conn.close()


async def handle_execute_query(config: DatabaseConfig, args: dict) -> dict:
    """Run a read-only SELECT/WITH query and return rows."""
    query = args.get("query", "").strip()
    if not query:
        return _err("'query' must not be empty.")

    error = validate_readonly(query)
    if error:
        return _err(error)

    params = args.get("params", [])
    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        cursor.execute(query, params)
        rows = rows_to_dict(cursor)
        return _ok({"row_count": len(rows), "rows": rows})
    finally:
        conn.close()


async def handle_list_tables(config: DatabaseConfig, args: dict) -> dict:
    """List user tables, optionally filtered by schema."""
    schema_filter = args.get("schema", "")
    query = """
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """
    params: list = []
    if schema_filter:
        query += " AND TABLE_SCHEMA = ?"
        params.append(schema_filter)
    query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"

    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        tables = rows_to_dict(cursor)
        return _ok({"table_count": len(tables), "tables": tables})
    finally:
        conn.close()


async def handle_describe_table(config: DatabaseConfig, args: dict) -> dict:
    """Return column metadata for a table."""
    table = args.get("table", "").strip()
    if not table:
        return _err("'table' must not be empty.")

    parts = table.split(".", 1)
    schema, tbl = (parts[0], parts[1]) if len(parts) == 2 else ("dbo", parts[0])

    query = """
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
    """
    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute(query, [schema, tbl])
        columns = rows_to_dict(cursor)
        if not columns:
            return _err(f"Table '{schema}.{tbl}' not found or has no columns.")
        return _ok({"table": f"{schema}.{tbl}", "columns": columns})
    finally:
        conn.close()


async def handle_get_row_count(config: DatabaseConfig, args: dict) -> dict:
    """Return the approximate row count for a table via system metadata."""
    table = args.get("table", "").strip()
    if not table:
        return _err("'table' must not be empty.")

    tbl_name = table.split(".")[-1]
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
        return _ok({"table": table, "row_count": count})
    finally:
        conn.close()
