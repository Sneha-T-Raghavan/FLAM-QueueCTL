## QueueCTL


# Objective
QueueCTL is a CLI-based job queue system for managing background jobs, handling retries, and maintaining a Dead Letter Queue (DLQ) for permanently failed jobs. It ensures job persistence, concurrent worker execution, and graceful shutdown behavior suitable for production-like environments.

# System Overview
QueueCTL consists of three core components:

- **Job Repository (SQLite)** – Stores all job metadata (state, attempts, schedule, DLQ, etc.)
- **Worker Engine** – Executes jobs in parallel, handles retries, and respects priority and scheduling.
- **CLI Interface** – Provides user-friendly commands for job management, configuration, and monitoring.

Each worker continuously polls for pending jobs (ordered by priority and schedule), executes them, and updates the database. Failed jobs are retried using exponential backoff until `max_retries` is reached, after which they move to the Dead Letter Queue (DLQ).

# Features
 - Enqueue and manage background jobs
 - Parallel worker execution with locking
 - Retry mechanism with exponential backoff
 - Automatic DLQ handling for exhausted retries
 - Persistent storage across restarts (JSON/SQLite)
 - Configurable retry count and backoff base
 - Graceful worker shutdown
 - User-friendly CLI interface

# Project Structure
├──queuectl/
    ├── cli.py
    ├── config.py
    ├── worker.py 
    ├── repository.py 
    ├── db.py 
    ├── utils.py 
    ├── models.py
    ├── logs/ 
├──README.md
├──pyproject.toml


# Setup Instructions

1. Clone repository
2. Run: pip install -e .
3. Run: queuectl config get

# Default Cofig Settings 
- Backoff Base : 2
- Max Retries Default : 3
- Timeout Seconds : 20 

## Command Reference

| **#** | **Action** | **Syntax** | **Example** |
|:--:|:--|:--|:--|
| **1** | Enqueue Job | `queuectl enqueue --id <id> --cmd "python -c "<command>"" --max-retries <n> --priority <p>` | `queuectl enqueue --id job1 --cmd "python -c "print(42)"" --max-retries 2`<br>`queuectl enqueue --id longjob6 --cmd "python script.py" --max-retries 0` |
| **2** | Start Worker(s) | `queuectl worker start --count <n>` | `queuectl worker start --count 3` |
| **3** | Stop Workers | *(Keyboard shortcut)* | `Ctrl + C` |
| **4** | Check System Status | `queuectl status` | *(Displays total jobs in each state)* |
| **5** | List Jobs by Status | `queuectl list --state `| `queuectl list --state pending` |
| **6** | Check Dead Letter Queue (DLQ) | `queuectl dlq list` | *(Lists failed jobs after max retries)* |
| **7** | Retry Job from DLQ | `queuectl dlq retry <id>` | `queuectl dlq retry job1` |
| **8** | Update Configuration | `queuectl config set <key> <value>` | `queuectl config set backoff_base 3`<br>`queuectl config set max_retries_default 4`<br>`queuectl config set timeout_seconds 30` |


# Quick Demo

-> Enqueue jobs<br>
queuectl enqueue --id fast --cmd "python -c \"print('fast job')\"" --priority 1
queuectl enqueue --id slow --cmd "python sleep30.py" --priority 5 --delay 10s

-> Start 2 workers<br>
queuectl worker start --count 2

-> Check system status<br>
queuectl status

-> View job logs<br>
type logs\fast.log


# Author
Sneha T Raghavan