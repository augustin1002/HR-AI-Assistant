"""
database/db.py
Builds and connects to the SQLite database from HRDataset_v14.csv
"""
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "HRDataset_v14.csv"
DB_PATH = BASE_DIR / "data" / "hr.db"
TABLE_NAME = "employees"


def build_database(csv_path: Path = CSV_PATH, db_path: Path = DB_PATH) -> None:
    """Read the HR CSV and load it into a SQLite table, cleaning column names."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # Clean column names: strip whitespace and any leftover BOM artifacts
    df.columns = [c.strip().replace("\ufeff", "").replace("ï»¿", "") for c in df.columns]
    df.columns = [c.replace(" ", "_") for c in df.columns]

    # Clean whitespace in string columns (this dataset has trailing spaces)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    conn = sqlite3.connect(db_path)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()
    print(f"Loaded {len(df)} rows into {db_path} (table: {TABLE_NAME})")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    if not Path(db_path).exists():
        build_database()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema_description(db_path: Path = DB_PATH) -> str:
    """Return a human/LLM-readable description of the table schema, used to
    ground natural-language-to-SQL generation."""
    conn = get_connection(db_path)
    cur = conn.execute(f"PRAGMA table_info({TABLE_NAME})")
    cols = [row["name"] for row in cur.fetchall()]
    conn.close()
    return (
        f"Table `{TABLE_NAME}` columns: " + ", ".join(cols) +
        "\nNotes: Salary is annual salary (numeric). PerformanceScore is text "
        "(e.g. 'Exceeds', 'Fully Meets', 'Needs Improvement', 'PIP'). "
        "Department is text (e.g. 'IT/IS', 'Production', 'Sales'). "
        "Termd = 1 means terminated, 0 means active. EmploymentStatus is text "
        "(e.g. 'Active', 'Voluntarily Terminated', 'Terminated for Cause')."
    )


if __name__ == "__main__":
    build_database()
