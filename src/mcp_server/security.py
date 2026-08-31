"""Security policy for the read-only CherryStock DuckDB MCP surface."""

from __future__ import annotations

import re


_ALLOWED_LEADING_KEYWORDS = {"SELECT", "WITH"}

_FORBIDDEN_KEYWORDS = {
    "ALTER",
    "ATTACH",
    "CALL",
    "CHECKPOINT",
    "COPY",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "EXPORT",
    "IMPORT",
    "INSERT",
    "INSTALL",
    "LOAD",
    "MERGE",
    "PRAGMA",
    "SET",
    "TRUNCATE",
    "UPDATE",
    "VACUUM",
}

_FORBIDDEN_FUNCTIONS = {
    "delta_scan",
    "glob",
    "http_get",
    "http_post",
    "iceberg_scan",
    "mysql_scan",
    "postgres_scan",
    "read_blob",
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_parquet",
    "sqlite_scan",
}

_EXTERNAL_URI_MARKERS = (
    "azure://",
    "file://",
    "gs://",
    "http://",
    "https://",
    "s3://",
)

_FILE_LITERAL_RE = re.compile(
    r"""(?ix)
    ['"][^'"]*\.(?:
        csv|csv\.gz|json|jsonl|ndjson|parquet|duckdb|db|sqlite|xlsx|xls
    )['"]
    """
)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*(?:\n|$)")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _remove_comments(sql: str) -> str:
    without_blocks = _BLOCK_COMMENT_RE.sub(" ", sql)
    return _LINE_COMMENT_RE.sub(" ", without_blocks)


def validate_readonly_sql(sql: str) -> str:
    """Validate and normalize one read-only SQL statement.

    The generic MCP SQL tool is intentionally conservative. It allows only
    SELECT/WITH statements against the already-open CherryStock database and
    blocks statements/functions that could mutate state, attach databases,
    load extensions, read local files, or reach external URLs.
    """

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL must be a non-empty string.")

    statement = _remove_comments(sql).strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()

    if not statement:
        raise ValueError("SQL must contain a statement.")

    if ";" in statement:
        raise ValueError("Multiple SQL statements are not allowed.")

    first_match = re.match(r"([A-Za-z]+)", statement)
    first_keyword = first_match.group(1).upper() if first_match else ""
    if first_keyword not in _ALLOWED_LEADING_KEYWORDS:
        raise ValueError("Only SELECT/WITH statements are allowed.")

    upper_statement = statement.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", upper_statement):
            raise ValueError(f"Forbidden SQL keyword: {keyword}")

    lower_statement = statement.lower()
    for function_name in _FORBIDDEN_FUNCTIONS:
        if re.search(rf"\b{re.escape(function_name)}\s*\(", lower_statement):
            raise ValueError(f"Forbidden DuckDB function: {function_name}")

    for marker in _EXTERNAL_URI_MARKERS:
        if marker in lower_statement:
            raise ValueError(f"External URI access is not allowed: {marker}")

    if _FILE_LITERAL_RE.search(statement):
        raise ValueError("Local/external file literals are not allowed.")

    return statement


def clamp_query_limit(requested: int, maximum: int) -> int:
    """Validate a row limit and cap it to the server-wide maximum."""

    if isinstance(requested, bool) or not isinstance(requested, int):
        raise ValueError("max_rows must be an integer.")
    if requested < 1:
        raise ValueError("max_rows must be greater than zero.")
    if maximum < 1:
        raise ValueError("maximum must be greater than zero.")
    return min(requested, maximum)
