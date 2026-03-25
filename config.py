"""
config.py — Load and validate database connection settings from environment variables.
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    server: str
    database: str
    username: str
    password: str
    port: int = 1433
    trust_server_certificate: bool = False
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Build config from environment variables, raising if required vars are missing."""
        required = {
            "MSSQL_SERVER": os.environ.get("MSSQL_SERVER", ""),
            "MSSQL_DATABASE": os.environ.get("MSSQL_DATABASE", ""),
            "MSSQL_USER": os.environ.get("MSSQL_USER", ""),
            "MSSQL_PASSWORD": os.environ.get("MSSQL_PASSWORD", ""),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            server=required["MSSQL_SERVER"],
            database=required["MSSQL_DATABASE"],
            username=required["MSSQL_USER"],
            password=required["MSSQL_PASSWORD"],
            port=int(os.environ.get("MSSQL_PORT", "1433")),
            trust_server_certificate=os.environ.get("MSSQL_TRUST_CERT", "false").lower() == "true",
            timeout=int(os.environ.get("MSSQL_TIMEOUT", "30")),
        )

    def to_connection_string(self) -> str:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
        )
        if self.trust_server_certificate:
            conn_str += "TrustServerCertificate=yes;"
        return conn_str
