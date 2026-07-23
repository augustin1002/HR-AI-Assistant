"""mcp_tools/datetime_tool.py - current date/time and simple date math."""
from datetime import datetime, timedelta


def current_datetime() -> str:
    return datetime.now().strftime("%A, %d %B %Y, %I:%M %p")


def days_between(date1: str, date2: str, fmt: str = "%m/%d/%Y") -> str:
    try:
        d1 = datetime.strptime(date1, fmt)
        d2 = datetime.strptime(date2, fmt)
        return str(abs((d2 - d1).days))
    except Exception as e:
        return f"Could not parse dates: {e}"


def add_days(date_str: str, days: int, fmt: str = "%m/%d/%Y") -> str:
    try:
        d = datetime.strptime(date_str, fmt)
        return (d + timedelta(days=days)).strftime(fmt)
    except Exception as e:
        return f"Could not parse date: {e}"
