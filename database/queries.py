"""
database/queries.py
Safe, read-only SQL execution against the HR SQLite database, plus a few
canned queries used directly by the router for common questions.
"""
import re
import pandas as pd
from database.db import get_connection

# Only allow read-only statements - this is a safety guard, not a full SQL
# sanitizer. The DB user should also be least-privilege in production.
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|pragma|create|replace)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(Exception):
    pass


def run_query(sql: str) -> pd.DataFrame:
    """Execute a read-only SQL query and return a DataFrame."""
    if _FORBIDDEN.search(sql):
        raise UnsafeQueryError(
            "Only read-only SELECT queries are allowed against this database."
        )
    if not sql.strip().lower().startswith("select"):
        raise UnsafeQueryError("Query must start with SELECT.")

    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


# ---- Canned / helper queries used by the rule-based router ----

def highest_salary(n: int = 1) -> pd.DataFrame:
    return run_query(
        f"SELECT Employee_Name, Department, Position, Salary "
        f"FROM employees ORDER BY Salary DESC LIMIT {int(n)}"
    )


def lowest_salary(n: int = 1) -> pd.DataFrame:
    return run_query(
        f"SELECT Employee_Name, Department, Position, Salary "
        f"FROM employees ORDER BY Salary ASC LIMIT {int(n)}"
    )


def count_by_department(dept: str) -> pd.DataFrame:
    return run_query(
        "SELECT Department, COUNT(*) as EmployeeCount FROM employees "
        f"WHERE Department LIKE '%{dept}%' GROUP BY Department"
    )


def low_performance_employees(limit: int = 20) -> pd.DataFrame:
    return run_query(
        "SELECT Employee_Name, Department, PerformanceScore, Absences "
        "FROM employees WHERE PerformanceScore IN ('PIP', 'Needs Improvement') "
        f"LIMIT {int(limit)}"
    )


def employees_on_probation_like() -> pd.DataFrame:
    # This dataset doesn't have an explicit "probation" flag, so we approximate
    # using EmploymentStatus / recency of hire; flagged clearly to the user.
    return run_query(
        "SELECT Employee_Name, Department, DateofHire, EmploymentStatus "
        "FROM employees WHERE EmploymentStatus = 'Active' "
        "ORDER BY DateofHire DESC LIMIT 20"
    )


def find_employee(name_fragment: str) -> pd.DataFrame:
    safe = name_fragment.replace("'", "''")
    return run_query(
        "SELECT * FROM employees WHERE Employee_Name LIKE "
        f"'%{safe}%' LIMIT 5"
    )


def employees_reporting_to(manager_fragment: str) -> pd.DataFrame:
    safe = manager_fragment.replace("'", "''")
    return run_query(
        "SELECT Employee_Name, Position, Department FROM employees "
        f"WHERE ManagerName LIKE '%{safe}%'"
    )


def absences_above(threshold: int) -> pd.DataFrame:
    return run_query(
        "SELECT Employee_Name, Department, Absences FROM employees "
        f"WHERE Absences > {int(threshold)} ORDER BY Absences DESC"
    )
