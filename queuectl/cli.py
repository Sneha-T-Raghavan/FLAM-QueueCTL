import json
import click

from .db import init_db, connect_db
from .repository import (
    enqueue_job, list_jobs, counts, dlq_list, dlq_retry,
    get_config, set_config
)
from .worker import start_workers


@click.group(help="queuectl — background job queue CLI")
def cli():
    # Ensure DB/schema exist before any command runs
    init_db()


# ---------- Enqueue ----------
@cli.command("enqueue", help="Add a new job to the queue")
@click.option("--id", "job_id", required=True, help="Job ID")
@click.option("--cmd", "command", required=True, help="Command to execute")
@click.option("--max-retries", default=None, type=int, help="Override max retry count")
@click.option("--priority", default=0, type=int, show_default=True,
              help="Lower number = higher priority (min-heap style)")
@click.option("--run-at", default=None,
              help="ISO datetime. If ends with Z = UTC; otherwise treated as IST (e.g., 2025-11-09T10:30:00)")
@click.option("--delay", "delay_str", default=None,
              help="Run after a delay, e.g. 20s, 5m, 1h30m, 2d3h (mutually exclusive with --run-at)")
def enqueue_cmd(job_id, command, max_retries, priority, run_at, delay_str):
    conn = connect_db()
    try:
        if run_at and delay_str:
            raise click.ClickException("Use either --run-at or --delay, not both.")

        delay_seconds = None
        if delay_str:
            from .utils import parse_delay_to_seconds
            delay_seconds = parse_delay_to_seconds(delay_str)

        enqueue_job(
            conn,
            job_id=job_id,
            command=command,
            max_retries=max_retries,
            priority=priority,
            run_at=run_at,
            delay_seconds=delay_seconds,
        )
        click.secho(
            f"Enqueued {job_id} -> `{command}` (priority={priority}, "
            f"{'delay='+delay_str if delay_str else ('run_at='+run_at if run_at else 'run_at=now')})",
            fg="green"
        )
    except (ValueError, RuntimeError, click.ClickException) as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)
    finally:
        conn.close()


# ---------- Workers ----------
@cli.group("worker", help="Manage workers")
def worker_group():
    pass


@worker_group.command("start")
@click.option("--count", type=int, default=1, show_default=True, help="Number of worker threads")
def worker_start(count):
    click.secho(f"Starting {count} worker(s). Press Ctrl+C to stop…", fg="cyan")
    start_workers(count)
    click.secho("Workers stopped.", fg="yellow")


# ---------- Jobs ----------
@cli.command("list")
@click.option("--state", type=click.Choice(["pending", "processing", "completed", "failed", "dead"]), default=None)
def list_cmd(state):
    conn = connect_db()
    try:
        rows = list_jobs(conn, state=state)
    finally:
        conn.close()

    if not rows:
        click.echo("No jobs.")
        return

    for r in rows:
        click.echo(
            f"{r['id']:>20} | {r['state']:<10} | attempts={r['attempts']}/{r['max_retries']} "
            f"| next={r['next_run_at']} | cmd={r['command']} | last_error={r['last_error']}"
        )


@cli.command("status")
def status_cmd():
    conn = connect_db()
    try:
        click.echo(json.dumps(counts(conn), indent=2))
    finally:
        conn.close()


# ---------- DLQ ----------
@cli.group("dlq", help="Dead Letter Queue")
def dlq_group():
    pass


@dlq_group.command("list")
def dlq_list_cmd():
    conn = connect_db()
    try:
        rows = dlq_list(conn)
    finally:
        conn.close()

    if not rows:
        click.echo("DLQ is empty.")
        return

    for r in rows:
        click.echo(f"{r['id']} | attempts={r['attempts']} | last_error={r['last_error']} | cmd={r['command']}")


@dlq_group.command("retry")
@click.argument("job_id")
def dlq_retry_cmd(job_id):
    conn = connect_db()
    try:
        if dlq_retry(conn, job_id):
            click.secho(f"Re-queued DLQ job {job_id}.", fg="green")
        else:
            raise click.ClickException(f"Job {job_id} not found in DLQ.")
    except click.ClickException as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)
    finally:
        conn.close()


# ---------- Config ----------
@cli.group("config", help="Configuration")
def config_group():
    pass


@config_group.command("get")
def config_get():
    conn = connect_db()
    try:
        click.echo(json.dumps(get_config(conn), indent=2))
    finally:
        conn.close()


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key, value):
    conn = connect_db()
    try:
        set_config(conn, key, value)
        click.secho(f"Config updated: {key}={value}", fg="green")
    except ValueError as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)
    finally:
        conn.close()


def main():
    cli()
