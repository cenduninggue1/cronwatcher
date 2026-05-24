"""CLI sub-command: cronwatcher env-check

Runs pre-flight environment checks for all configured jobs and prints
a human-readable report. Exits with code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronwatcher.config import Config
from cronwatcher.env_check import CheckResult, check_all_jobs


def add_env_check_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "env-check",
        help="verify environment requirements for all configured jobs",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="stop after the first job that fails a check",
    )


def cmd_env_check(args: argparse.Namespace, cfg: Config) -> int:
    """Execute the env-check sub-command. Returns an exit code."""
    results: List[CheckResult] = []

    for job in cfg.jobs:
        from cronwatcher.env_check import check_job_environment

        result = check_job_environment(job)
        results.append(result)
        print(str(result))

        if not result.ok and args.fail_fast:
            print("\n[fail-fast] stopping after first failure.", file=sys.stderr)
            return 1

    failures = [r for r in results if not r.ok]
    if failures:
        print(
            f"\n{len(failures)}/{len(results)} job(s) failed environment checks.",
            file=sys.stderr,
        )
        return 1

    print(f"\nAll {len(results)} job(s) passed environment checks.")
    return 0
