"""
database.py — Low-level database connection and query utilities.
"""

import logging

import pyodbc

from .config import DatabaseConfig

logger = logging.getLogger("sqlserver-mcp.database")

# Keywords that must never appear as the first word of a query.
BLOCKED_KEYWORDS: frozenset[str] = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "MERGE", "REPLACE", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "DENY", "BULK",
})

ALLOWED_KEYWORDS: frozenset[str] = frozenset({"SELECT", "WITH"})


def get_connection(config: DatabaseConfig) -> pyodbc.Connection:
    """Open and return a pyodbc connection."""
    conn_str = config.to_connection_string()
    logger.debug("Connecting to %s / %s", config.server, config.database)
    return pyodbc.connect(conn_str, timeout=config.timeout)


def rows_to_dict(cursor: pyodbc.Cursor) -> list[dict]:
    """Convert cursor rows to a list of plain dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def validate_readonly(query: str) -> str | None:
    """
    Return an error message if *query* is not a safe read-only statement,
    or None if it passes validation.
    """
    first_word = query.split()[0].upper() if query.split() else ""
    if first_word in BLOCKED_KEYWORDS:
        return (
            f"'{first_word}' statements are not allowed. "
            "This server is read-only — only SELECT / WITH queries are permitted."
        )
    if first_word not in ALLOWED_KEYWORDS:
        return "Only SELECT / WITH queries are permitted. This server is read-only."
    return None
