"""
__main__.py — Entry point.
Run with:  python -m sqlserver_mcp
"""

import asyncio
import logging

from .config import DatabaseConfig
from .server import serve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    config = DatabaseConfig.from_env()
    asyncio.run(serve(config))


if __name__ == "__main__":
    main()
