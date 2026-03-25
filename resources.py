"""
resources.py — Resource templates for SQL Server metadata (read-only).

Provides reusable resource templates for:
  - Tables
  - Views
  - Stored Procedures
  - Columns
  - Parameters

All queries are read-only and safe for MCP usage.
"""

import re
from fastmcp import FastMCP


# -----------------------------
# 🔒 Basic identifier validation
# -----------------------------
_VALID_NAME = re.compile(r"^[A-Za-z0-9_\.\[\]]+$")


def _validate(name: str, field: str) -> str:
    """Basic validation to prevent SQL injection via object names."""
    if not name or not _VALID_NAME.match(name):
        raise ValueError(f"Invalid {field}: {name}")
    return name


# -----------------------------
# 📦 Resource Registration
# -----------------------------
def register(mcp: FastMCP) -> None:
    """Register all SQL Server metadata resource templates."""

    # -------------------------
    # 📋 List all tables
    # -------------------------
    @mcp.resource(
        name="list_tables",
        description="List all user tables in the database",
    )
    def list_tables():
        return """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """

    # -------------------------
    # 📊 Table columns
    # -------------------------
    @mcp.resource(
        name="table_columns",
        description="Get column details for a table",
    )
    def table_columns(table_name: str):
        table_name = _validate(table_name, "table_name")
        return f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """

    # -------------------------
    # 👁️ List views
    # -------------------------
    @mcp.resource(
        name="list_views",
        description="List all views in the database",
    )
    def list_views():
        return """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """

    # -------------------------
    # 🧾 View definition
    # -------------------------
    @mcp.resource(
        name="view_definition",
        description="Get SQL definition of a view",
    )
    def view_definition(view_name: str):
        view_name = _validate(view_name, "view_name")
        return f"""
        SELECT OBJECT_DEFINITION(OBJECT_ID('{view_name}')) AS definition
        """

    # -------------------------
    # ⚙️ List stored procedures
    # -------------------------
    @mcp.resource(
        name="list_stored_procedures",
        description="List all stored procedures",
    )
    def list_stored_procedures():
        return """
        SELECT SPECIFIC_SCHEMA, SPECIFIC_NAME
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
        ORDER BY SPECIFIC_SCHEMA, SPECIFIC_NAME
        """

    # -------------------------
    # 📜 Stored procedure definition
    # -------------------------
    @mcp.resource(
        name="stored_procedure_definition",
        description="Get SQL definition of a stored procedure",
    )
    def stored_procedure_definition(sp_name: str):
        sp_name = _validate(sp_name, "sp_name")
        return f"""
        SELECT OBJECT_DEFINITION(OBJECT_ID('{sp_name}')) AS definition
        """

    # -------------------------
    # 🧩 Stored procedure parameters
    # -------------------------
    @mcp.resource(
        name="stored_procedure_parameters",
        description="Get parameters of a stored procedure",
    )
    def stored_procedure_parameters(sp_name: str):
        sp_name = _validate(sp_name, "sp_name")
        return f"""
        SELECT PARAMETER_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.PARAMETERS
        WHERE SPECIFIC_NAME = '{sp_name}'
        ORDER BY ORDINAL_POSITION
        """

    # -------------------------
    # 🔍 Search objects (tables/views/SPs)
    # -------------------------
    @mcp.resource(
        name="search_objects",
        description="Search tables, views, or stored procedures by name",
    )
    def search_objects(keyword: str):
        keyword = _validate(keyword, "keyword")
        return f"""
        SELECT 'TABLE' AS type, TABLE_NAME AS name
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%{keyword}%'

        UNION ALL

        SELECT 'VIEW', TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_NAME LIKE '%{keyword}%'

        UNION ALL

        SELECT 'PROCEDURE', SPECIFIC_NAME
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
          AND SPECIFIC_NAME LIKE '%{keyword}%'
        ORDER BY type, name
        """