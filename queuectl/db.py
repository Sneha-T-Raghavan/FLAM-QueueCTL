import os
import sqlite3
from .config import DEFAULT_CONFIG

DB_FILE = os.environ.get("QUEUECTL_DB", "queue.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    max_retries INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    next_run_at TEXT,
    last_error TEXT,
    picked_by TEXT,
    priority INTEGER DEFAULT 0,
    duration_seconds REAL
);

CREATE INDEX IF NOT EXISTS idx_jobs_state_next ON jobs(state, next_run_at);
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

def connect_db():
    conn = sqlite3.connect("queue.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

def init_db():
    conn = connect_db()
    with conn:
        for stmt in SCHEMA.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(s + ";")
        # seed defaults
        for k, v in DEFAULT_CONFIG.items():
            conn.execute(
                "INSERT OR IGNORE INTO config(key, value) VALUES(?,?)", (k, v)
            )
    conn.close()
