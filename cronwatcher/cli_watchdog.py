"""CLI sub-commands for watchdog inspection and remediation."""

from __future__ import annotations

import argparse
import sys

from cronwatcher.config import Config
from cronwatcher.watchdog import find_hung_jobs, mark_hung_jobs


def add_watchdog_subparser(sub: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = sub.add_parser("watchdog", help="Inspect or resolve hung cron jobs")
    p.add_argument(
        "--config", required=True, metavar="FILE", help="Path to config YAML"
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Seconds before a started-but-unfinished job is considered hung (default: 3600)",
    )
    p.add_argument(
        "--fix",
        action="store_true",
        help="Mark hung jobs as failed (exit_code=-1) instead of just listing them",
    )


def cmd_watchdog(args: argparse.Namespace) -> int:
    try:
        cfg = Config.load(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 2

    if args.fix:
        jobs = mark_hung_jobs(cfg.db_path, timeout_seconds=args.timeout)
        verb = "Marked"
    else:
        jobs = find_hung_jobs(cfg.db_path, timeout_seconds=args.timeout)
        verb = "Found"

    if not jobs:
        print("No hung jobs detected.")
        return 0

    print(f"{verb} {len(jobs)} hung job(s):")
    for j in jobs:
        print(
            f"  [{j.run_id}] {j.job_name} "
            f"started={j.started_at.isoformat()} "
            f"running={j.running_seconds:.0f}s"
        )
    return 1
