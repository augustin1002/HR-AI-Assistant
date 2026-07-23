"""
mcp_tools/server.py
Optional: exposes the same tools as a real MCP server (stdio transport) so
this HR assistant's tools can be plugged into any MCP-compatible client
(e.g. Claude Desktop), not just the built-in Streamlit agent.

Run with:  python -m mcp_tools.server
Requires:  pip install "mcp[cli]"
"""
from mcp.server.fastmcp import FastMCP

from mcp_tools.sql_tool import query_database
from mcp_tools.calculator import calculate
from mcp_tools.datetime_tool import current_datetime, days_between
from mcp_tools.file_tool import list_documents, search_documents

mcp = FastMCP("hr-ai-assistant")


@mcp.tool()
def sql_query(sql: str) -> str:
    """Run a read-only SELECT query against the employees table and return results."""
    return query_database(sql)


@mcp.tool()
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression, e.g. '62506 * 0.12'."""
    return calculate(expression)


@mcp.tool()
def now() -> str:
    """Return the current date and time."""
    return current_datetime()


@mcp.tool()
def date_diff(date1: str, date2: str) -> str:
    """Return the number of days between two dates (MM/DD/YYYY format)."""
    return days_between(date1, date2)


@mcp.tool()
def list_policy_documents() -> str:
    """List all indexed HR policy documents."""
    return list_documents()


@mcp.tool()
def search_policy_documents(keyword: str) -> str:
    """Keyword-search the raw text of HR policy documents."""
    return search_documents(keyword)


if __name__ == "__main__":
    mcp.run(transport="stdio")
