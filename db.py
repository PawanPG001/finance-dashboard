"""
db.py — SQLite data layer for the Personal Finance Dashboard.

Keeps all DB access in one place so app.py stays focused on UI.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date

DB_PATH = "finance.db"

DEFAULT_CATEGORIES = [
    "Salary", "Freelance", "Investments",           # income-ish
    "Rent", "Groceries", "Utilities", "Transport",
    "Dining Out", "Entertainment", "Health",
    "Shopping", "Travel", "Education", "Other",
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('Income', 'Expense'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            )
            """
        )


def add_transaction(txn_date, description, category, amount, txn_type):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (date, description, category, amount, type) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(txn_date), description, category, float(amount), txn_type),
        )


def add_transactions_bulk(rows):
    """rows: list of tuples (date, description, category, amount, type)"""
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO transactions (date, description, category, amount, type) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def delete_transaction(txn_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))


def get_all_transactions():
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
        return [dict(r) for r in cur.fetchall()]


def set_budget(category, monthly_limit):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (category, float(monthly_limit)),
        )


def get_budgets():
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM budgets")
        return {r["category"]: r["monthly_limit"] for r in cur.fetchall()}


def delete_budget(category):
    with get_conn() as conn:
        conn.execute("DELETE FROM budgets WHERE category = ?", (category,))
