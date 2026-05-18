#!/usr/bin/env python3
"""Run a command with a wall-clock timeout and clear failure metadata."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--label", default="command")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("missing command after --")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")

    started_at = datetime.now(timezone.utc).isoformat()
    print(
        f"[timeout-wrapper] label={args.label} timeout_seconds={args.timeout_seconds} "
        f"started_at={started_at}",
        flush=True,
    )
    try:
        result = subprocess.run(command, timeout=args.timeout_seconds, check=False)
    except subprocess.TimeoutExpired as exc:
        ended_at = datetime.now(timezone.utc).isoformat()
        print(
            f"[timeout-wrapper] label={args.label} status=timeout "
            f"timeout_seconds={args.timeout_seconds} ended_at={ended_at}",
            file=sys.stderr,
            flush=True,
        )
        return 124 if exc.timeout else 1

    ended_at = datetime.now(timezone.utc).isoformat()
    print(
        f"[timeout-wrapper] label={args.label} status=exit "
        f"exit_code={result.returncode} ended_at={ended_at}",
        flush=True,
    )
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
