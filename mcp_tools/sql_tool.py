"""
mcp_tools/sql_tool.py
Agent-facing wrapper around database.queries.run_query. Formats results as
a readable string (rather than a raw DataFrame) for the LLM / chat UI.
"""
from database.queries import run_query, UnsafeQueryError


def query_database(sql: str, max_rows: int = 25) -> str:
    try:
        df = run_query(sql)
    except UnsafeQueryError as e:
        return f"Query rejected: {e}"
    except Exception as e:
        return f"Query failed: {e}"

    if df.empty:
        return "No matching rows found."
    truncated = df.head(max_rows)
    note = "" if len(df) <= max_rows else f"\n(showing first {max_rows} of {len(df)} rows)"
    return truncated.to_string(index=False) + note
