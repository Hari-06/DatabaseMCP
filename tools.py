"""
tools.py — MCP Tool schema definitions (no business logic).
"""

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="test_connection",
        description="Verify that the MCP server can connect to SQL Server and return its version.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="execute_query",
        description=(
            "Execute a read-only SELECT (or WITH/CTE) query and return results as JSON. "
            "INSERT, UPDATE, DELETE, DROP, CREATE, ALTER and all other write operations are blocked."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A read-only SELECT or WITH query.",
                },
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "Optional positional parameters for parameterised queries.",
                    "default": [],
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="list_tables",
        description="List all user tables in the current database, optionally filtered by schema.",
        inputSchema={
            "type": "object",
            "properties": {
                "schema": {
                    "type": "string",
                    "description": "Schema name to filter by (e.g. 'dbo'). Omit to list all schemas.",
                },
            },
        },
    ),
    Tool(
        name="describe_table",
        description="Return column names, data types, nullability, and ordinal position for a table.",
        inputSchema={
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Table name, optionally schema-qualified (e.g. 'dbo.Customers').",
                },
            },
            "required": ["table"],
        },
    ),
    Tool(
        name="get_row_count",
        description="Return the approximate row count for a table using SQL Server system metadata.",
        inputSchema={
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Table name, optionally schema-qualified.",
                },
            },
            "required": ["table"],
        },
    ),
]
