"""CLI sub-command: snapshot — show a point-in-time view of all job statuses."""

from __future__ import annotations

import argparse
import sys

from cronwatcher.config import Config
from cronwatcher.snapshot import build_snapshot, format_snapshot


def add_snapshot_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "snapshot",
        help="Print a point-in-time status snapshot of all configured jobs.",
    )
    p.add_argument(
        "--stale-only",
        action="store_true",
        default=False,
        help="Only show jobs that are stale or hung.",
    )
    p.set_defaults(func=cmd_snapshot)


def cmd_snapshot(args: argparse.Namespace, config: Config, db_path: str) -> int:
    snapshots = build_snapshot(config, db_path)

    if args.stale_only:
        snapshots = [s for s in snapshots if s.is_stale or s.is_hung]
        if not snapshots:
            print("All jobs appear healthy.")
            return 0

    print(format_snapshot(snapshots))
    return 0
