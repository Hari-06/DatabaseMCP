"""
db/validator.py — Query safety validation.

Ensures only read-only SQL statements (SELECT / WITH) are executed.
All write and DDL keywords are explicitly blocked.
"""

BLOCKED_KEYWORDS: frozenset[str] = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "MERGE", "REPLACE", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "DENY", "BULK",
})

ALLOWED_KEYWORDS: frozenset[str] = frozenset({"SELECT", "WITH"})


def validate_readonly(query: str) -> str | None:
    """Check that *query* is a read-only statement.

    Returns an error message string if the query is not permitted,
    or None if it passes validation.
    """
    words = query.split()
    if not words:
        return "Query must not be empty."

    first = words[0].upper()

    if first in BLOCKED_KEYWORDS:
        return (
            f"'{first}' statements are not allowed. "
            "This server is read-only — only SELECT / WITH queries are permitted."
        )
    if first not in ALLOWED_KEYWORDS:
        return "Only SELECT / WITH queries are permitted. This server is read-only."

    return None
