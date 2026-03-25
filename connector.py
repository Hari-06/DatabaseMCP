"""
db/connector.py — Database connection factory and low-level query helpers.

Responsible for:
- Opening pyodbc connections from a DatabaseConfig
- Converting cursor rows to plain dicts
"""

import logging

import pyodbc

from ..config import DatabaseConfig

logger = logging.getLogger("sqlserver-mcp.db.connector")


def get_connection(config: DatabaseConfig) -> pyodbc.Connection:
    """Open and return a pyodbc connection for the given config."""
    logger.debug(
        "Opening connection to %s:%s / %s",
        config.server, config.port, config.database,
    )
    return pyodbc.connect(config.to_connection_string(), timeout=config.timeout)


def rows_to_dict(cursor: pyodbc.Cursor) -> list[dict]:
    """Fetch all rows from *cursor* and return them as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
