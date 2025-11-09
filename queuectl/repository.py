import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Iterable

from .utils import now_iso, iso_in_utc_from_seconds_from_now
from .models import PENDING, PROCESSING, COMPLETED, DEAD
from .config import ALLOWED_CONFIG_KEYS


# ---------- Config ----------
def get_config(conn) -> Dict[str, str]:
    cur = conn.execute("SELECT key, value FROM config")
    return {r["key"]: r["value"] for r in cur.fetchall()}


def set_config(conn, key: str, value: str):
    if key not in ALLOWED_CONFIG_KEYS:
        raise ValueError(f"Allowed keys: {', '.join(sorted(ALLOWED_CONFIG_KEYS))}")
    with conn:
        conn.execute(
            "INSERT INTO config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


# ---------- Jobs: enqueue / claim / complete / retry ----------
def enqueue_job(
    conn,
    *,
    job_id: str,
    command: str,
    max_retries: Optional[int] = None,
    priority: int = 0,
    run_at: Optional[str] = None,       # may be IST (no Z) or UTC Z
    delay_seconds: Optional[int] = None # parsed from --delay
):
    if not job_id or not job_id.strip():
        raise ValueError("Job id cannot be empty.")
    if not command or not command.strip():
        raise ValueError("Command cannot be empty.")
    if delay_seconds is not None and delay_seconds <= 0:
        raise ValueError("delay must be > 0 seconds")

    cfg = get_config(conn)
    try:
        mret = int(max_retries if max_retries is not None else cfg.get("max_retries_default", "3"))
    except ValueError:
        raise ValueError("max_retries must be an integer.")

    ts = now_iso()

    # Compute next_run_at
    if delay_seconds is not None:
        next_at = iso_in_utc_from_seconds_from_now(delay_seconds)
    elif run_at:
        # If the user passed UTC with 'Z', take as-is.
        if run_at.endswith("Z"):
            next_at = run_at
        else:
            # Interpret as IST (UTC+05:30)
            try:
                local_dt = datetime.fromisoformat(run_at)
            except Exception as e:
                raise ValueError(f"Invalid --run-at format: {run_at} ({e})")
            utc_dt = local_dt - timedelta(hours=5, minutes=30)
            next_at = utc_dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        next_at = ts

    exists = conn.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
    if exists:
        raise ValueError(f"Job '{job_id}' already exists.")

    try:
        with conn:
            conn.execute(
                """INSERT INTO jobs
                   (id, command, state, attempts, max_retries, created_at, updated_at, next_run_at, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, command, PENDING, 0, mret, ts, ts, next_at, int(priority)),
            )
    except sqlite3.Error as e:
        raise RuntimeError(f"DB error while inserting job: {e}")


def claim_one(conn, worker_name: str) -> Optional[sqlite3.Row]:
    now = now_iso()
    with conn:
        row = conn.execute(
            """SELECT id FROM jobs
               WHERE state=? AND (next_run_at IS NULL OR next_run_at <= ?)
               ORDER BY priority ASC, created_at ASC
               LIMIT 1""",
            (PENDING, now),
        ).fetchone()
        if not row:
            return None
        job_id = row["id"]
        updated = conn.execute(
            "UPDATE jobs SET state=?, picked_by=?, updated_at=? WHERE id=? AND state=?",
            (PROCESSING, worker_name, now, job_id, PENDING),
        )
        if updated.rowcount != 1:
            return None
        return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def complete(conn, job_id: str):
    with conn:
        conn.execute(
            "UPDATE jobs SET state=?, updated_at=?, picked_by=NULL WHERE id=?",
            (COMPLETED, now_iso(), job_id),
        )


def schedule_retry(conn, job_row: sqlite3.Row, base: int, error: str):
    attempts = job_row["attempts"] + 1
    delay = base ** attempts
    next_at = (datetime.utcnow() + timedelta(seconds=delay)).isoformat() + "Z"

    if attempts >= job_row["max_retries"]:
        # Move to DLQ
        with conn:
            conn.execute(
                """UPDATE jobs
                   SET state=?, attempts=?, updated_at=?, next_run_at=NULL, last_error=?, picked_by=NULL
                   WHERE id=?""",
                (DEAD, attempts, now_iso(), error[:500], job_row["id"]),
            )
    else:
        with conn:
            conn.execute(
                """UPDATE jobs
                   SET state=?, attempts=?, updated_at=?, next_run_at=?, last_error=?, picked_by=NULL
                   WHERE id=?""",
                (PENDING, attempts, now_iso(), next_at, error[:500], job_row["id"]),
            )


# ---------- Queries ----------
def list_jobs(conn, state: Optional[str] = None) -> Iterable[sqlite3.Row]:
    if state:
        return conn.execute(
            "SELECT * FROM jobs WHERE state=? ORDER BY priority ASC, created_at ASC",
            (state,),
        ).fetchall()
    return conn.execute("SELECT * FROM jobs ").fetchall()


def counts(conn) -> Dict[str, int]:
    out = {}
    # 'failed' is not a persisted terminal state; kept for CLI compatibility (always 0)
    for s in ("pending", "processing", "completed", "failed", "dead"):
        out[s] = conn.execute(
            "SELECT COUNT(1) AS c FROM jobs WHERE state=?",
            (s,),
        ).fetchone()["c"]
    return out


# ---------- DLQ ----------ORDER BY created_at
def dlq_list(conn) -> Iterable[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM jobs WHERE state='dead' ORDER BY updated_at DESC"
    ).fetchall()


def dlq_retry(conn, job_id: str) -> bool:
    if not job_id or not job_id.strip():
        raise ValueError("Job id cannot be empty.")
    try:
        with conn:
            res = conn.execute(
                """UPDATE jobs
                   SET state='pending', attempts=0, updated_at=?, next_run_at=?, last_error=NULL, picked_by=NULL
                   WHERE id=? AND state='dead'""",
                (now_iso(), now_iso(), job_id),
            )
        return res.rowcount == 1
    except sqlite3.Error as e:
        raise RuntimeError(f"DB error during DLQ retry: {e}")
