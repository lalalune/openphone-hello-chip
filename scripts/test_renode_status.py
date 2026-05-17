#!/usr/bin/env python3
"""Unit tests for scripts/run_renode.sh status reporting."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_RENODE = ROOT / "scripts/run_renode.sh"
RENODE_ELF = ROOT / "build/qemu/hello_qemu_firmware.elf"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [str(RUN_RENODE), "--check"],
        cwd=ROOT,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"missing {expected!r} in output:\n{text}")


def test_missing_renode_is_non_strict_blocked() -> None:
    result = run_check({"PATH": "/usr/bin:/bin", "REQUIRE_RENODE": "0"})
    if result.returncode != 0:
        raise AssertionError(f"expected non-strict blocked check to exit 0, got {result.returncode}\n{result.stdout}")
    assert_contains(result.stdout, "STATUS: PASS renode.semantic")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.run")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.check")


def test_missing_renode_is_strict_blocked() -> None:
    result = run_check({"PATH": "/usr/bin:/bin", "REQUIRE_RENODE": "1"})
    if result.returncode != 2:
        raise AssertionError(f"expected strict blocked check to exit 2, got {result.returncode}\n{result.stdout}")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.run")


def test_fake_renode_with_firmware_still_blocks_without_transcript_check() -> None:
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td)
        renode = bindir / "renode"
        write_executable(renode, "#!/bin/sh\nexit 0\n")
        RENODE_ELF.parent.mkdir(parents=True, exist_ok=True)
        RENODE_ELF.write_text("fake elf\n")
        result = run_check({"PATH": f"{bindir}:/usr/bin:/bin", "REQUIRE_RENODE": "0"})
    if result.returncode != 0:
        raise AssertionError(f"expected transcript-blocked check to exit 0, got {result.returncode}\n{result.stdout}")
    assert_contains(result.stdout, "STATUS: PASS renode.semantic")
    assert_contains(result.stdout, "automated Renode serial transcript check")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.check")


def main() -> int:
    tests = [
        test_missing_renode_is_non_strict_blocked,
        test_missing_renode_is_strict_blocked,
        test_fake_renode_with_firmware_still_blocks_without_transcript_check,
    ]
    saved = RENODE_ELF.read_bytes() if RENODE_ELF.is_file() else None
    try:
        for test in tests:
            test()
            print(f"PASS {test.__name__}")
    finally:
        if saved is None:
            RENODE_ELF.unlink(missing_ok=True)
        else:
            RENODE_ELF.parent.mkdir(parents=True, exist_ok=True)
            RENODE_ELF.write_bytes(saved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
