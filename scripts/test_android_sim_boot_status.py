#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "scripts/boot_android_simulator.sh"
CHECK = ROOT / "scripts/check_android_sim_boot.py"
REPORT = ROOT / "build/reports/android_sim_boot.json"


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"missing {expected!r} in output:\n{text}")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_boot_script_blocks_without_aosp_dir() -> None:
    result = run([str(BOOT)])
    if result.returncode != 2:
        raise AssertionError(
            f"expected boot script to block, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "BLOCKED: AOSP_DIR is not set")
    data = json.loads(REPORT.read_text())
    if data.get("schema") != "openphone.android_sim_boot.v1":
        raise AssertionError("android sim report schema mismatch")
    if data.get("status") != "blocked":
        raise AssertionError("android sim report must be blocked without AOSP_DIR")
    if "not hello-chip hardware ABI proof" not in data.get("claim_boundary", ""):
        raise AssertionError("android sim report must keep the hello-chip ABI boundary explicit")


def test_checker_reports_blocked_report() -> None:
    if not REPORT.is_file():
        test_boot_script_blocks_without_aosp_dir()
    result = run([sys.executable, str(CHECK)])
    if result.returncode != 2:
        raise AssertionError(
            f"expected checker to return blocked, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "Android simulator boot blocked")
    assert_contains(result.stdout, "AOSP_DIR")


def main() -> int:
    saved = REPORT.read_bytes() if REPORT.is_file() else None
    try:
        for test in (test_boot_script_blocks_without_aosp_dir, test_checker_reports_blocked_report):
            test()
            print(f"PASS {test.__name__}")
    finally:
        if saved is None:
            REPORT.unlink(missing_ok=True)
        else:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_bytes(saved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
