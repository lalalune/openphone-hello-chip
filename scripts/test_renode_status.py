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
RENODE_LOG = ROOT / "build/reports/renode_smoke.log"
RENODE_MANIFEST = ROOT / "build/reports/renode_smoke.manifest"
BANNER = "openphone hello qemu"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_script(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [str(RUN_RENODE), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def run_check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return run_script(["--check"], env)


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"missing {expected!r} in output:\n{text}")


def test_missing_renode_is_non_strict_blocked() -> None:
    result = run_check({"PATH": "/usr/bin:/bin", "REQUIRE_RENODE": "0"})
    if result.returncode != 0:
        raise AssertionError(
            f"expected non-strict blocked check to exit 0, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "STATUS: PASS renode.semantic")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.run")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.check")
    assert_contains(result.stdout, "Renode install/preflight")
    assert_contains(result.stdout, "Renode executable missing: command -v renode failed")
    assert_contains(result.stdout, "version unavailable because renode --version could not run")
    assert_contains(
        result.stdout, "scripts/run_renode.sh --check --transcript path/to/real-renode-serial.log"
    )


def test_missing_renode_is_strict_blocked() -> None:
    result = run_check({"PATH": "/usr/bin:/bin", "REQUIRE_RENODE": "1"})
    if result.returncode != 2:
        raise AssertionError(
            f"expected strict blocked check to exit 2, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "STATUS: BLOCKED renode.run")
    assert_contains(result.stdout, "Renode executable missing: command -v renode failed")


def test_renode_with_firmware_still_blocks_without_transcript() -> None:
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td)
        renode = bindir / "renode"
        write_executable(renode, "#!/bin/sh\nprintf 'Renode test double 0.0\\n'\n")
        RENODE_ELF.parent.mkdir(parents=True, exist_ok=True)
        RENODE_ELF.write_text("unit-test elf placeholder\n")
        result = run_check({"PATH": f"{bindir}:/usr/bin:/bin", "REQUIRE_RENODE": "0"})
    if result.returncode != 0:
        raise AssertionError(
            f"expected transcript-blocked check to exit 0, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "STATUS: PASS renode.semantic")
    assert_contains(result.stdout, "STATUS: PASS renode.preflight")
    assert_contains(result.stdout, "no real transcript was provided")
    assert_contains(result.stdout, "STATUS: BLOCKED renode.check")


def test_invalid_transcript_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as td:
        transcript = Path(td) / "renode.log"
        transcript.write_text("Renode started but no banner appeared\n")
        result = run_script(["--check", "--transcript", str(transcript)], {"PATH": "/usr/bin:/bin"})
    if result.returncode != 1:
        raise AssertionError(
            f"expected invalid transcript to exit 1, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "STATUS: PASS renode.semantic")
    assert_contains(result.stdout, "STATUS: FAIL renode.transcript")


def test_valid_transcript_intake_archives_manifest() -> None:
    with tempfile.TemporaryDirectory() as td:
        transcript = Path(td) / "renode.log"
        transcript.write_text(f"Renode serial analyzer\n{BANNER}\n")
        result = run_script(["--check", "--transcript", str(transcript)], {"PATH": "/usr/bin:/bin"})
    if result.returncode != 0:
        raise AssertionError(
            f"expected valid transcript intake to exit 0, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "STATUS: PASS renode.transcript")
    assert_contains(result.stdout, "STATUS: PASS renode.run")
    assert_contains(result.stdout, "STATUS: PASS renode.check")
    if not RENODE_LOG.is_file() or BANNER not in RENODE_LOG.read_text(errors="ignore"):
        raise AssertionError("expected archived Renode transcript to contain banner")
    manifest = RENODE_MANIFEST.read_text(errors="ignore") if RENODE_MANIFEST.is_file() else ""
    assert_contains(manifest, "status=PASS")
    assert_contains(manifest, f"banner={BANNER}")
    assert_contains(manifest, "renode_version=unavailable-missing-executable")


def main() -> int:
    tests = [
        test_missing_renode_is_non_strict_blocked,
        test_missing_renode_is_strict_blocked,
        test_renode_with_firmware_still_blocks_without_transcript,
        test_invalid_transcript_fails_closed,
        test_valid_transcript_intake_archives_manifest,
    ]
    saved = RENODE_ELF.read_bytes() if RENODE_ELF.is_file() else None
    saved_log = RENODE_LOG.read_bytes() if RENODE_LOG.is_file() else None
    saved_manifest = RENODE_MANIFEST.read_bytes() if RENODE_MANIFEST.is_file() else None
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
        if saved_log is None:
            RENODE_LOG.unlink(missing_ok=True)
        else:
            RENODE_LOG.parent.mkdir(parents=True, exist_ok=True)
            RENODE_LOG.write_bytes(saved_log)
        if saved_manifest is None:
            RENODE_MANIFEST.unlink(missing_ok=True)
        else:
            RENODE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
            RENODE_MANIFEST.write_bytes(saved_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
