import threading
import time
import signal
import shlex
import subprocess
from .db import connect_db
from .repository import claim_one, complete, schedule_retry, get_config

_stop = threading.Event()


def setup_signal_handlers():
    def _handler(signum, frame):
        print(f"\n[Main] Received signal {signum}. Stopping workers")
        _stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except Exception:
            pass


def safe_run_command(cmd: str, timeout: int = 10) -> int:
    import shlex, subprocess

    try:
        args = shlex.split(cmd, posix=(not subprocess._mswindows))
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout 
        )

        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"[Error] Command timed out after {timeout}s: {cmd}")
        return 124  # Common exit code for timeout
    except FileNotFoundError:
        print(f"[Error] Command not found: {cmd}")
        return 127
    except Exception as e:
        print(f"[Error] Exception while running command '{cmd}': {e}")
        return 1

def worker_loop(name: str):
    conn = connect_db()
    try:
        cfg = get_config(conn)
        base = int(cfg.get("backoff_base", "2"))
        timeout = int(cfg.get("timeout_seconds", "20"))
    except Exception as e:
        print(f"[{name}] Warning: could not load config ({e}); using defaults.")
        base = 2
        timeout = 20

    while not _stop.is_set():
        try:
            job = claim_one(conn, worker_name=name)
            if not job:
                time.sleep(0.5)
                continue

            print(f"[{name}] Executing job: {job['id']} → {job['command']}")
            rc = safe_run_command(job["command"], timeout=timeout)

            if rc == 0:
                print(f"[{name}] Job {job['id']} completed successfully.")
                complete(conn, job["id"])
            else:
                print(f"[{name}] Job {job['id']} failed with code {rc}, scheduling retry...")
                schedule_retry(conn, job, base=base, error=f"exit_code={rc}")

        except Exception as e:
            print(f"[{name}] Unexpected error: {e}")
            time.sleep(1)

    conn.close()
    print(f"[{name}] Worker stopped.")


def start_workers(count: int):
    """Start multiple worker threads."""
    setup_signal_handlers()
    threads = []

    for i in range(count):
        t = threading.Thread(target=worker_loop, args=(f"worker-{i+1}",), daemon=True)
        t.start()
        threads.append(t)
        print(f"[System] Started {t.name}")

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
    finally:
        _stop.set()
        for t in threads:
            t.join()
        print("[System] All workers stopped gracefully.")

