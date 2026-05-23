"""Command-line interface for cronwatcher."""
from __future__ import annotations

import argparse
import sys
from datetime import timezone
from pathlib import Path

from cronwatcher.config import Config
from cronwatcher.db import get_connection, init_db
from cronwatcher.history import get_recent_runs
from cronwatcher.retention import prune_runs
from cronwatcher.scheduler import run_due_jobs
from cronwatcher.summary import summarise_all_jobs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Lightweight cron job monitor",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="cronwatcher.yaml",
        help="Path to configuration file (default: cronwatcher.yaml)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("run", help="Evaluate schedules and run any due jobs")

    hist = sub.add_parser("history", help="Show recent runs for a job")
    hist.add_argument("job", help="Job name")
    hist.add_argument("-n", "--limit", type=int, default=10, help="Number of runs")

    sub.add_parser("summary", help="Print a summary of all jobs")

    sub.add_parser("prune", help="Remove old run records per retention policy")

    return parser


def cmd_run(cfg: Config) -> int:
    with get_connection(cfg.database_path) as conn:
        init_db(conn)
        run_due_jobs(cfg, conn)
    return 0


def cmd_history(cfg: Config, job_name: str, limit: int) -> int:
    with get_connection(cfg.database_path) as conn:
        runs = get_recent_runs(conn, job_name, limit)
    if not runs:
        print(f"No runs found for job '{job_name}'.")
        return 0
    print(f"{'START':<26} {'STATUS':<10} {'DURATION':>10}  COMMAND")
    print("-" * 70)
    for r in runs:
        status = "OK" if r.succeeded else "FAIL"
        dur = f"{r.duration_seconds:.1f}s" if r.duration_seconds is not None else "—"
        start = r.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"{start:<26} {status:<10} {dur:>10}  {r.command}")
    return 0


def cmd_summary(cfg: Config) -> int:
    with get_connection(cfg.database_path) as conn:
        summaries = summarise_all_jobs(conn)
    if not summaries:
        print("No job data available.")
        return 0
    print(f"{'JOB':<30} {'TOTAL':>6} {'OK':>6} {'FAIL':>6} {'FAIL%':>7}")
    print("-" * 60)
    for s in summaries:
        print(f"{s.job_name:<30} {s.total_runs:>6} {s.successful_runs:>6} "
              f"{s.failed_runs:>6} {s.failure_rate * 100:>6.1f}%")
    return 0


def cmd_prune(cfg: Config) -> int:
    with get_connection(cfg.database_path) as conn:
        removed = prune_runs(conn, cfg.retention)
    print(f"Pruned {removed} run record(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Error: config file not found: {cfg_path}", file=sys.stderr)
        return 2
    cfg = Config.load(cfg_path)

    if args.command == "run":
        return cmd_run(cfg)
    if args.command == "history":
        return cmd_history(cfg, args.job, args.limit)
    if args.command == "summary":
        return cmd_summary(cfg)
    if args.command == "prune":
        return cmd_prune(cfg)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
