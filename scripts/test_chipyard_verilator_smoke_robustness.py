#!/usr/bin/env python3
"""Robustness tests for generated Chipyard Verilator smoke recovery."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_chipyard_verilator_linux_smoke as smoke  # noqa: E402


def test_partial_generated_driver_dir_is_repairable_blocker() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        old_values = (
            smoke.GENERATED_CONFIG_DIR,
            smoke.GENERATED_DRIVER_DIR,
            smoke.GENERATED_DRIVER_MAKEFILE,
            smoke.GENERATED_FILELISTS,
            smoke.GENERATED_SIMULATOR,
        )
        try:
            smoke.GENERATED_CONFIG_DIR = (
                tmp / "generated-src" / "chipyard.harness.TestHarness.OpenPhoneRocketConfig"
            )
            smoke.GENERATED_DRIVER_DIR = (
                smoke.GENERATED_CONFIG_DIR / "chipyard.harness.TestHarness.OpenPhoneRocketConfig"
            )
            smoke.GENERATED_DRIVER_MAKEFILE = smoke.GENERATED_DRIVER_DIR / "VTestDriver.mk"
            smoke.GENERATED_FILELISTS = (smoke.GENERATED_CONFIG_DIR / "sim_files.f",)
            smoke.GENERATED_SIMULATOR = tmp / "simulator-chipyard.harness-OpenPhoneRocketConfig"
            smoke.GENERATED_DRIVER_DIR.mkdir(parents=True)

            blockers = smoke.generated_path_blockers()
            joined = "\n".join(blockers)
            if "partial generated Verilator" not in joined:
                raise AssertionError(f"expected partial generated blocker, got {blockers}")

            status = smoke.repair_stale_generated_paths()
            if status != 0:
                raise AssertionError(f"expected repair status 0, got {status}")
            if smoke.GENERATED_CONFIG_DIR.exists():
                raise AssertionError("expected generated config directory to be removed")
        finally:
            (
                smoke.GENERATED_CONFIG_DIR,
                smoke.GENERATED_DRIVER_DIR,
                smoke.GENERATED_DRIVER_MAKEFILE,
                smoke.GENERATED_FILELISTS,
                smoke.GENERATED_SIMULATOR,
            ) = old_values


def test_zero_byte_driver_outputs_are_repairable_blockers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        old_values = (
            smoke.GENERATED_CONFIG_DIR,
            smoke.GENERATED_DRIVER_DIR,
            smoke.GENERATED_DRIVER_MAKEFILE,
            smoke.GENERATED_FILELISTS,
            smoke.GENERATED_SIMULATOR,
        )
        try:
            smoke.GENERATED_CONFIG_DIR = (
                tmp / "generated-src" / "chipyard.harness.TestHarness.OpenPhoneRocketConfig"
            )
            smoke.GENERATED_DRIVER_DIR = (
                smoke.GENERATED_CONFIG_DIR / "chipyard.harness.TestHarness.OpenPhoneRocketConfig"
            )
            smoke.GENERATED_DRIVER_MAKEFILE = smoke.GENERATED_DRIVER_DIR / "VTestDriver.mk"
            smoke.GENERATED_FILELISTS = (smoke.GENERATED_CONFIG_DIR / "sim_files.f",)
            smoke.GENERATED_SIMULATOR = tmp / "simulator-chipyard.harness-OpenPhoneRocketConfig"
            smoke.GENERATED_DRIVER_DIR.mkdir(parents=True)
            smoke.GENERATED_DRIVER_MAKEFILE.write_text("VM_PREFIX = /tmp/tool\n", encoding="utf-8")
            (smoke.GENERATED_DRIVER_DIR / "VTestDriver__ALL.a").write_bytes(b"")

            blockers = smoke.generated_path_blockers()
            joined = "\n".join(blockers)
            if "zero-byte model artifacts" not in joined:
                raise AssertionError(f"expected zero-byte generated blocker, got {blockers}")
        finally:
            (
                smoke.GENERATED_CONFIG_DIR,
                smoke.GENERATED_DRIVER_DIR,
                smoke.GENERATED_DRIVER_MAKEFILE,
                smoke.GENERATED_FILELISTS,
                smoke.GENERATED_SIMULATOR,
            ) = old_values


def test_log_metadata_records_attempt_and_closed_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        old_log = smoke.LOG
        try:
            smoke.LOG = tmp / "verilator-linux-smoke.log"
            smoke.LOG.write_text(
                "\n".join(
                    [
                        "openphone-evidence: attempt=2",
                        "openphone-evidence: clean_generated=1",
                        "openphone-evidence: raw_transcript_begin",
                        "build output",
                        "openphone-evidence: raw_transcript_end",
                        "openphone-evidence: exit_code=2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            metadata = smoke.parse_log_metadata()
            if metadata["attempt"] != "2":
                raise AssertionError(f"expected attempt metadata, got {metadata}")
            if metadata["clean_generated"] != "1":
                raise AssertionError(f"expected clean metadata, got {metadata}")
            if metadata["raw_transcript_closed"] is not True:
                raise AssertionError(f"expected closed transcript, got {metadata}")
        finally:
            smoke.LOG = old_log


def main() -> int:
    tests = (
        test_partial_generated_driver_dir_is_repairable_blocker,
        test_zero_byte_driver_outputs_are_repairable_blockers,
        test_log_metadata_records_attempt_and_closed_transcript,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
