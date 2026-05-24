"""CLI sub-command: cronwatcher stale — list jobs that haven't run recently."""

from __future__ import annotations

import argparse
import sys

from cronwatcher.config import Config
from cronwatcher.stale import find_stale_jobs


def add_stale_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "stale",
        help="List jobs that have not run within their expected interval.",
    )
    p.add_argument(
        "--exit-zero",
        action="store_true",
        default=False,
        help="Always exit with code 0, even when stale jobs are found.",
    )
    p.set_defaults(func=cmd_stale)


def cmd_stale(args: argparse.Namespace, cfg: Config) -> int:
    """Print stale jobs to stdout.  Returns exit-code 1 if any are found.

    If ``--exit-zero`` is passed the exit code is always 0, which is useful
    when running cronwatcher inside a CI pipeline where a non-zero exit would
    fail the build even for informational stale checks.
    """
    stale = find_stale_jobs(cfg.db_path, cfg.jobs)

    if not stale:
        print("All jobs are running on schedule.")
        return 0

    print(f"{'Job':<30} {'Last Run (UTC)':<24} {'Interval (min)':<16} {'Overdue (min)'}")
    print("-" * 82)
    for s in stale:
        last = s.last_run_at.isoformat(timespec="seconds") if s.last_run_at else "never"
        print(
            f"{s.job_name:<30} {last:<24} {s.expected_interval_minutes:<16} {s.minutes_overdue}"
        )

    return 0 if args.exit_zero else 1
