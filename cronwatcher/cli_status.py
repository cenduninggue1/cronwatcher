"""CLI sub-command: `cronwatcher status` — prints daemon health to stdout."""

from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace

from cronwatcher.config import Config
from cronwatcher.status import get_daemon_status, format_status


def add_status_subparser(subparsers) -> None:  # type: ignore[type-arg]
    """Register the *status* sub-command onto an existing subparsers action."""
    p: ArgumentParser = subparsers.add_parser(
        "status",
        help="Show daemon health and recent job statistics.",
    )
    p.add_argument(
        "--overdue",
        type=int,
        default=120,
        metavar="SECONDS",
        help="Seconds without a heartbeat before the daemon is considered overdue (default: 120).",
    )


def cmd_status(args: Namespace, cfg: Config) -> int:
    """Handler for `cronwatcher status`.  Returns an exit code."""
    try:
        status = get_daemon_status(cfg.database, overdue_seconds=args.overdue)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: could not read status — {exc}", file=sys.stderr)
        return 1

    print(format_status(status))

    # Exit 0 when healthy, 2 when degraded so callers can script on it.
    return 0 if status.healthy else 2
