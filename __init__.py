"""db — database connectivity and validation helpers."""

from .connector import get_connection, rows_to_dict
from .validator import validate_readonly

__all__ = ["get_connection", "rows_to_dict", "validate_readonly"]
