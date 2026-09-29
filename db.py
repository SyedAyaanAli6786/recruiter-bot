"""
db.py — Raw SQLite connection and query helpers.

All SQL is hand-written here and in the callers.
No ORM, no query builder.
"""

import sqlite3
import os

DB_PATH = os.environ.get("RECRUITER_DB", os.path.join(os.path.dirname(__file__), "recruiter.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection() -> sqlite3.Connection:
    """Return a new connection with row_factory set so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows accessible by column name
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrent read performance
    return conn


def init_db() -> None:
    """Create all tables from schema.sql if they don't already exist."""
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    with get_connection() as conn:
        conn.executescript(sql)


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return all rows as plain dicts."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetchone(sql: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT and return the first row as a plain dict, or None."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE and return lastrowid."""
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def executemany(sql: str, param_list: list[tuple]) -> None:
    """Execute the same statement for a list of parameter tuples (bulk insert)."""
    with get_connection() as conn:
        conn.executemany(sql, param_list)
        conn.commit()


def executescript(sql: str) -> None:
    """Execute a raw multi-statement SQL script (DDL, seed, etc.)."""
    with get_connection() as conn:
        conn.executescript(sql)
