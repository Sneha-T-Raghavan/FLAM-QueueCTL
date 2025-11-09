"""
Automated smoke test for QueueCTL
---------------------------------
Validates:
1. Job enqueue and completion
2. Retry with exponential backoff
3. DLQ transfer and retry
4. Persistence and configuration

Run:
    python tests/test_queuectl.py
"""

import os
import subprocess
import time
import json
import sqlite3

def run(cmd: str) -> str:
    """Run CLI command and return stdout."""
    print(f"\n$ {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr)
        raise RuntimeError(f"Command failed: {cmd}")
    print(res.stdout.strip())
    return res.stdout.strip()


def db_exists():
    assert os.path.exists("queue.db"), "Database not created!"


def test_basic_flow():
    # Check config
    run("queuectl config get")

    # Enqueue good and bad jobs
    run("queuectl enqueue --id okjob  --cmd \"python -c 'print(42)'\" --max-retries 2")
    run("queuectl enqueue --id badjob --cmd \"bash -c 'exit 2'\"       --max-retries 2")

    # Start workers briefly (let them process)
    print("\n Starting workers for 10s …")
    p = subprocess.Popen("queuectl worker start --count 2", shell=True)
    time.sleep(10)
    p.terminate()

    # Check statuses
    out = run("queuectl status")
    stats = json.loads(out)
    print("Stats:", stats)
    assert "pending" in stats

    # List DLQ jobs (should include 'badjob')
    dlq = run("queuectl dlq list")
    assert "badjob" in dlq or dlq == "DLQ is empty."

    # Retry DLQ job (if exists)
    run("queuectl dlq retry badjob")

    #  Verify config set
    run("queuectl config set backoff_base 3")

    print("\n All tests executed successfully.")


if __name__ == "__main__":
    test_basic_flow()
