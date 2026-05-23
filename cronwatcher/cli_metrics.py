"""CLI sub-command: cronwatcher metrics — display runtime counters and gauges."""

from __future__ import annotations

import argparse
from typing import List

from cronwatcher.metrics import get_registry, format_snapshot


def add_metrics_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "metrics",
        help="Display current runtime metrics (counters and gauges).",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    p.set_defaults(func=cmd_metrics)


def cmd_metrics(args: argparse.Namespace) -> int:
    """Print current metrics to stdout. Returns exit code."""
    registry = get_registry()
    snap = registry.snapshot()

    if args.output_format == "json":
        import json

        payload = {
            "collected_at": snap.collected_at.isoformat(),
            "counters": snap.counters,
            "gauges": snap.gauges,
        }
        print(json.dumps(payload, indent=2))
        return 0

    # Default: human-readable text
    lines: List[str] = format_snapshot(snap)
    if len(lines) == 1:  # only the header line — no metrics registered
        lines.append("  (no metrics recorded yet)")
    for line in lines:
        print(line)
    return 0
