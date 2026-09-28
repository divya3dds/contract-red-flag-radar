import sqlite3
import json
from datetime import datetime

DB_NAME = "contracts.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            clauses TEXT NOT NULL,
            results TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_analysis(title, clauses, results):
    conn = get_connection()
    conn.execute(
        "INSERT INTO analyses (title, created_at, clauses, results) VALUES (?, ?, ?, ?)",
        (title, datetime.now().strftime("%d %b %Y, %H:%M"), json.dumps(clauses), json.dumps(results)),
    )
    conn.commit()
    conn.close()


def list_analyses():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, created_at FROM analyses ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def load_analysis(analysis_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT title, clauses, results FROM analyses WHERE id = ?", (analysis_id,)
    ).fetchone()
    conn.close()
    return {
        "title": row[0],
        "clauses": json.loads(row[1]),
        "results": json.loads(row[2]),
        "saved": True,
    }