"""
server.py — FastMCP server for SQL Server (read-only).

Tools are registered with @mcp.tool() decorators.
FastMCP auto-generates schemas from type hints and docstrings —
no manual Tool definitions, no list_tools / call_tool wiring needed.
"""

import logging

from fastmcp import FastMCP

from .config import DatabaseConfig
from .database import get_connection, rows_to_dict, validate_readonly

logger = logging.getLogger("sqlserver-mcp")

mcp = FastMCP(
    name="sqlserver-mcp",
    instructions=(
        "Read-only MCP server for SQL Server. "
        "Only SELECT and WITH queries are permitted. "
        "All write operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked."
    ),
)

# Module-level config — injected at startup via serve()
_config: DatabaseConfig | None = None


def _get_config() -> DatabaseConfig:
    if _config is None:
        raise RuntimeError("Server not initialised. Call serve() first.")
    return _config


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def test_connection() -> dict:
    """Verify connectivity to SQL Server and return version information."""
    config = _get_config()
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

    config = _get_config()
    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        cursor.execute(query, params or [])
        rows = rows_to_dict(cursor)
        return {"row_count": len(rows), "rows": rows}
    finally:
        conn.close()


@mcp.tool()
def list_tables(schema: str | None = None) -> dict:
    """
    List all user tables in the current database.

    Args:
        schema: Optional schema name to filter by (e.g. 'dbo').
    """
    config = _get_config()
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

    config = _get_config()
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


@mcp.tool()
def get_row_count(table: str) -> dict:
    """
    Return the approximate row count for a table using SQL Server system metadata.

    Args:
        table: Table name, optionally schema-qualified.
    """
    tbl_name = table.strip().split(".")[-1]
    config = _get_config()
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


# ── Startup ───────────────────────────────────────────────────────────────────

def serve(config: DatabaseConfig) -> None:
    """Inject config and start the MCP server on stdio."""
    global _config
    _config = config
    logger.info(
        "SQL Server MCP server starting (db=%s@%s:%s)",
        config.database, config.server, config.port,
    )
    mcp.run()
