# SQL Server MCP Server

A read-only MCP (Model Context Protocol) server for Microsoft SQL Server.  
Write operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked at the application level.

## Project Structure

```
sqlserver_mcp/
├── src/
│   └── sqlserver_mcp/
│       ├── __init__.py          # Package marker
│       ├── __main__.py          # Entry point (python -m sqlserver_mcp)
│       ├── config.py            # DatabaseConfig dataclass & env-var loading
│       ├── server.py            # FastMCP instance creation & startup
│       ├── db/
│       │   ├── __init__.py      # Re-exports connector + validator helpers
│       │   ├── connector.py     # pyodbc connection factory & rows_to_dict
│       │   └── validator.py     # Read-only query guard (blocked keywords)
│       └── tools/
│           ├── __init__.py      # register_all() — mounts every tool module
│           ├── connection.py    # test_connection tool
│           ├── query.py         # execute_query tool
│           ├── schema.py        # list_tables + describe_table tools
│           └── stats.py         # get_row_count tool
├── pyproject.toml               # Package metadata & dependencies
├── claude_desktop_config.json
└── README.md
```

## Requirements

- Python 3.11+
- [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

## Installation

```bash
pip install -e .
```

Or without installing:

```bash
pip install mcp pyodbc
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `MSSQL_SERVER` | *(required)* | Host, e.g. `myserver.database.windows.net` |
| `MSSQL_PORT` | `1433` | TCP port SQL Server is listening on |
| `MSSQL_DATABASE` | `*(required)*` | Target database name |
| `MSSQL_USER` | *(required)* | SQL Server login |
| `MSSQL_PASSWORD` | *(required)* | Password |
| `MSSQL_TRUST_CERT` | `false` | Set `true` for self-signed certs (dev only) |
| `MSSQL_TIMEOUT` | `30` | Connection timeout in seconds |

## Running

```bash
export MSSQL_SERVER=localhost
export MSSQL_DATABASE=MyDb
export MSSQL_USER=sa
export MSSQL_PASSWORD=YourPassword123

# As a module
python -m sqlserver_mcp

# Or if installed via pip
sqlserver-mcp
```

## Claude Desktop Integration

Paste the contents of `claude_desktop_config.json` into your Claude Desktop config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

## Available Tools

| Tool | Description |
|---|---|
| `test_connection` | Ping the DB and return SQL Server version |
| `list_tables` | List all user tables; optional schema filter |
| `describe_table` | Column names, types, nullability |
| `get_row_count` | Fast row count via system metadata |
| `execute_query` | Run SELECT / WITH queries → JSON rows |
