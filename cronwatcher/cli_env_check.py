"""CLI subcommand: env-check — verify required environment variables for jobs."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from cronwatcher.env_check import check_all_jobs, check_job_environment

if TYPE_CHECKING:
    from cronwatcher.config import Config


def add_env_check_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the *env-check* subcommand."""
    parser = subparsers.add_parser(
        "env-check",
        help="Check that required environment variables are present for each job.",
    )
    parser.add_argument(
        "--job",
        metavar="NAME",
        default=None,
        help="Only check the named job (default: check all jobs).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Suppress output; exit code reflects pass/fail.",
    )
    parser.set_defaults(func=cmd_env_check)


def cmd_env_check(args: argparse.Namespace, cfg: "Config") -> int:
    """Execute the env-check subcommand.

    Returns 0 when all checks pass, 1 when any check fails, 2 on usage error.
    """
    quiet: bool = getattr(args, "quiet", False)
    job_name: str | None = getattr(args, "job", None)

    if job_name is not None:
        # Find the requested job in the config.
        matching = [j for j in cfg.jobs if j.name == job_name]
        if not matching:
            print(
                f"env-check: no job named {job_name!r} found in config.",
                file=sys.stderr,
            )
            return 2
        results = [check_job_environment(matching[0])]
    else:
        results = check_all_jobs(cfg.jobs)

    all_ok = all(r.ok for r in results)

    if not quiet:
        for result in results:
            print(str(result))

        if all_ok:
            print("\nAll environment checks passed.")
        else:
            failed = [r for r in results if not r.ok]
            print(
                f"\n{len(failed)} of {len(results)} job(s) failed environment checks.",
                file=sys.stderr,
            )

    return 0 if all_ok else 1
