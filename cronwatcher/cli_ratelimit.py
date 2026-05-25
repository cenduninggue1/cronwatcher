"""CLI sub-command: ``cronwatcher ratelimit``

Allows operators to inspect and reset per-job alert rate-limit counters
without touching the database directly.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from cronwatcher.db import get_connection
from cronwatcher.ratelimit import (
    count_recent_alerts,
    prune_old_entries,
    record_rate_limit_alert,
)

if TYPE_CHECKING:
    from cronwatcher.config import Config


def add_ratelimit_subparser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "ratelimit",
        help="inspect or reset per-job alert rate-limit counters",
    )
    p.add_argument(
        "--window",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="sliding window in seconds (default: 3600)",
    )
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--show",
        metavar="JOB",
        help="print alert count for JOB within the window",
    )
    action.add_argument(
        "--reset",
        metavar="JOB",
        help="delete all rate-limit entries for JOB",
    )
    action.add_argument(
        "--prune",
        action="store_true",
        help="remove entries older than --window seconds",
    )


def cmd_ratelimit(args: argparse.Namespace, cfg: "Config") -> int:
    conn = get_connection(cfg.database)
    try:
        if args.show:
            count = count_recent_alerts(conn, args.show, args.window)
            print(f"{args.show}: {count} alert(s) in the last {args.window}s")
            return 0

        if args.reset:
            conn.execute(
                "DELETE FROM alert_rate_limit WHERE job_name = ?",
                (args.reset,),
            )
            conn.commit()
            print(f"Rate-limit counter reset for job '{args.reset}'.")
            return 0

        if args.prune:
            removed = prune_old_entries(conn, args.window)
            print(f"Pruned {removed} stale rate-limit entry/entries.")
            return 0

    finally:
        conn.close()

    return 1  # unreachable, satisfies type checker
