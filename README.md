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
2. pip install -e .
3. queuectl config get

# Default Cofig Settings 
Backoff Base : 2
Max Retries Default : 3
Timeout Seconds : 20 


# Syntax and Usage Examples
Run commands in CMD CLI env

1. Enqueue job

Attribute Explanation
--id : Needs to be unique for every job
--max-retries: Maximum number of times it will be requed automatically
--priority: Priority of task, lower number is higher priority
 --delay: For delayed execution by certain amount of time

queuectl enqueue --id <id>  --cmd "python -c '<command to be executed>'" --max-retries <max retries> --priority <number>    

Enqueue Multi-Line Commands Run as File
queuectl enqueue --id longjob6 --cmd "python <filename>.py" --max-retries 0

Example: queuectl enqueue --id job1  --cmd "python -c 'print(42)'" --max-retries 2

2. Start Worker(s)
queuectl worker start --count <number of workers to be started>

Example: queuectl worker start --count 3

3. Stop Workers

4. Check System Status
queuectl status

5. List Jobs by Status 
queuectl list --state <status>

Example: queuectl list --state pending

6. Check DLQ
queuectl dlq list

7. Retry DLQ Job
queuectl dlq retry <id>

Example: queuectl dlq retry job1

8. Update Configuration
queuectl config set <attribute> <number>

Examples: 
- queuectl config set backoff_base 3
- queuectl config set max_retries_default 4
- queuectl config set timeout_seconds 30

# Quick Demo

-> Enqueue jobs
queuectl enqueue --id fast --cmd "python -c \"print('fast job')\"" --priority 1
queuectl enqueue --id slow --cmd "python sleep30.py" --priority 5 --delay 10s

-> Start 2 workers
queuectl worker start --count 2

-> Check system status
queuectl status

-> View job logs
type logs\fast.log


# Author
Sneha T Raghavan