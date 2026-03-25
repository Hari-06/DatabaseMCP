"""
server.py — MCP server wiring.
Registers tools and routes incoming tool calls to the appropriate handler.
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent

from .config import DatabaseConfig
from .handlers import (
    handle_describe_table,
    handle_execute_query,
    handle_get_row_count,
    handle_list_tables,
    handle_test_connection,
)
from .tools import TOOLS

logger = logging.getLogger("sqlserver-mcp.server")

app = Server("sqlserver-mcp")


# ── serialisation helpers ─────────────────────────────────────────────────────

def _to_result(data: dict) -> CallToolResult:
    is_error = not data.pop("ok", True)
    text = json.dumps(data, default=str, indent=2)
    return CallToolResult(
        isError=is_error,
        content=[TextContent(type="text", text=text)],
    )


# ── MCP handlers ──────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    config: DatabaseConfig = app.state.db_config  # type: ignore[attr-defined]

    try:
        match name:
            case "test_connection":
                result = await handle_test_connection(config)
            case "execute_query":
                result = await handle_execute_query(config, arguments)
            case "list_tables":
                result = await handle_list_tables(config, arguments)
            case "describe_table":
                result = await handle_describe_table(config, arguments)
            case "get_row_count":
                result = await handle_get_row_count(config, arguments)
            case _:
                result = {"ok": False, "error": f"Unknown tool: '{name}'"}
    except Exception as exc:
        logger.exception("Unhandled error in tool '%s'", name)
        result = {"ok": False, "error": str(exc)}

    return _to_result(result)


# ── startup ───────────────────────────────────────────────────────────────────

async def serve(config: DatabaseConfig) -> None:
    """Start the MCP server on stdio."""
    app.state.db_config = config  # type: ignore[attr-defined]
    logger.info("SQL Server MCP server starting (db=%s@%s)", config.database, config.server)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
