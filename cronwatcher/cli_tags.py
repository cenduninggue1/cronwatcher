"""CLI sub-command: cronwatcher tags — list and filter jobs by tag."""

from __future__ import annotations

import argparse
import sys

from cronwatcher.config import Config
from cronwatcher.tags import (
    format_tag_summary,
    get_all_tags,
    get_jobs_by_tag,
    group_by_tag,
)


def add_tags_subparser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("tags", help="List jobs grouped by tag")
    p.add_argument(
        "--tag",
        metavar="TAG",
        default=None,
        help="Show only jobs carrying this tag",
    )
    p.add_argument(
        "--list-tags",
        action="store_true",
        help="Print every tag in use and exit",
    )


def cmd_tags(args: argparse.Namespace, cfg: Config) -> int:
    jobs = cfg.jobs

    if args.list_tags:
        tags = get_all_tags(jobs)
        if not tags:
            print("No tags defined.")
        else:
            for t in tags:
                print(t)
        return 0

    if args.tag:
        matched = get_jobs_by_tag(jobs, args.tag)
        if not matched:
            print(f"No jobs found with tag '{args.tag}'.", file=sys.stderr)
            return 1
        groups = {args.tag: matched}
    else:
        groups = group_by_tag(jobs)

    print(format_tag_summary(groups))
    return 0
