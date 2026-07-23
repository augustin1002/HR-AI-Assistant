"""
agent/router.py

Lightweight rule-based orchestrator (a deliberately simple stand-in for the
LangGraph/LangChain agent described in the project brief). It:

  1. Checks for direct tool intents (calculator, current date/time).
  2. Decides whether the question needs policy context (RAG), employee data
     (SQL), both, or neither.
  3. Gathers that context and asks the LLM to compose the final answer.

Why rule-based instead of LangGraph: it has zero extra dependencies, is
transparent to debug, and is easy to extend with more keywords/patterns.
Swap this file for a LangGraph StateGraph agent later without touching the
UI or the RAG/SQL/LLM layers - they're already decoupled for that.
"""
import os
import re

from rag.retriever import get_retriever
from database.queries import (
    highest_salary, lowest_salary, count_by_department,
    low_performance_employees, find_employee, employees_reporting_to,
    absences_above,
)
from database.db import get_schema_description
from mcp_tools.calculator import calculate
from mcp_tools.datetime_tool import current_datetime
from mcp_tools.sql_tool import query_database
from llm.model import complete
from llm.prompts import SYSTEM_PROMPT, build_prompt

POLICY_KEYWORDS = [
    "policy", "leave", "maternity", "paternity", "sick leave", "casual leave",
    "earned leave", "dress code", "code of conduct", "harassment",
    "confidential", "password", "mfa", "vpn", "security", "benefit",
    "insurance", "gratuity", "provident fund", "recruitment", "hiring",
    "probation", "notice period", "termination policy", "handbook",
    "reimbursement", "bonus", "conduct",
]

DATA_KEYWORDS = [
    "salary", "employee", "department", "manager", "performance score",
    "absences", "absent", "how many", "who has", "who earns", "list employees",
    "reports to", "reporting", "terminated", "hired", "engagement survey",
    "satisfaction", "special project",
]

CALC_PATTERN = re.compile(
    r"(what is|calculate|compute)\b.*\d.*(%|[+\-*/]).*\d|(\d+\s*%\s*of\s*\d+)", re.I
)
DATETIME_PATTERN = re.compile(r"\b(today'?s? date|current time|what time|what day)\b", re.I)


def _looks_like(keywords, text):
    text = text.lower()
    return any(k in text for k in keywords)


def _direct_tool_response(question: str):
    if DATETIME_PATTERN.search(question):
        return f"It's currently {current_datetime()}."
    if CALC_PATTERN.search(question):
        pct_match = re.search(r"([\d.]+)\s*%\s*of\s*([\d.]+)", question, re.I)
        if pct_match:
            expr = f"({pct_match.group(1)}/100)*{pct_match.group(2)}"
        else:
            expr = re.sub(r"[^\d\.\+\-\*/%\(\) ]", "", question)
        if expr.strip():
            return f"Result: {calculate(expr)}"
    return None


def _rag_context(question: str) -> str:
    retriever = get_retriever()
    hits = retriever.retrieve(question, k=4)
    if not hits:
        return ""
    return "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)


def _sql_context(question: str) -> str:
    """Try a few canned patterns first (fast, deterministic); fall back to
    asking the LLM to generate SQL against the known schema when a real
    provider is configured."""
    q = question.lower()

    m = re.search(r"highest salary", q)
    if m:
        return highest_salary(1).to_string(index=False)

    m = re.search(r"lowest salary", q)
    if m:
        return lowest_salary(1).to_string(index=False)

    m = re.search(r"how many employees.*(in|from)\s+([a-z/ ]+)", q)
    if m:
        return count_by_department(m.group(2).strip()).to_string(index=False)

    if "low performance" in q or "performance improvement" in q or "pip" in q:
        return low_performance_employees().to_string(index=False)

    m = re.search(r"reports? to ([a-z .]+)", q)
    if m:
        return employees_reporting_to(m.group(1).strip()).to_string(index=False)

    m = re.search(r"more than (\d+) absences", q)
    if m:
        return absences_above(int(m.group(1))).to_string(index=False)

    m = re.search(r"([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)'?s? (performance|salary|department)", question)
    if m:
        return find_employee(m.group(1)).to_string(index=False)

    # Fall back to LLM-generated SQL if a real provider is configured
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider != "mock":
        schema = get_schema_description()
        sql_prompt = (
            f"{schema}\n\nWrite ONE read-only SQLite SELECT query (no other text, "
            f"no markdown fences) that answers this question about the employees "
            f"table: \"{question}\""
        )
        sql = complete(sql_prompt, "You are a SQL generator. Output only the raw SQL query.")
        sql = sql.strip().strip("`").replace("sql\n", "").strip()
        if sql.lower().startswith("select"):
            return query_database(sql)
    return ""


def answer(question: str, chat_history: str = "") -> dict:
    """Main entry point. Returns {"answer": str, "route": str} for UI display."""
    direct = _direct_tool_response(question)
    if direct:
        return {"answer": direct, "route": "tool"}

    needs_policy = _looks_like(POLICY_KEYWORDS, question)
    needs_data = _looks_like(DATA_KEYWORDS, question)

    rag_ctx = _rag_context(question) if (needs_policy or not needs_data) else ""
    sql_ctx = _sql_context(question) if needs_data else ""

    if needs_policy and needs_data:
        route = "combined (RAG + SQL)"
    elif needs_data:
        route = "SQL"
    elif needs_policy:
        route = "RAG"
    else:
        route = "RAG (default)"

    prompt = build_prompt(question, rag_context=rag_ctx, sql_context=sql_ctx,
                           chat_history=chat_history)
    final_answer = complete(prompt, SYSTEM_PROMPT)
    return {"answer": final_answer, "route": route, "rag_context": rag_ctx, "sql_context": sql_ctx}
