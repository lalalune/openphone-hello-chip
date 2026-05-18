#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "scripts/boot_android_simulator.sh"
CHECK = ROOT / "scripts/check_android_sim_boot.py"
PREFLIGHT = ROOT / "scripts/check_aosp_linux_preflight.py"
REPORT = ROOT / "build/reports/android_sim_boot.json"
PREFLIGHT_REPORT = ROOT / "build/reports/aosp_linux_preflight.json"


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"missing {expected!r} in output:\n{text}")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("AOSP_DIR", None)
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
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
    missing_requirements = data.get("host_requirements", {}).get("missing", [])
    for requirement in (
        "AOSP_DIR is not set",
        "/dev/kvm is missing",
        "Cuttlefish launcher not found",
    ):
        if not any(requirement in item for item in missing_requirements):
            raise AssertionError(
                f"android sim report missing host requirement {requirement!r}: "
                f"{missing_requirements}"
            )
    for key in ("run_qemu", "run_renode"):
        if not isinstance(data.get(key), bool):
            raise AssertionError(f"android sim report must include boolean {key}")
    if data.get("evidence_manifest") != "docs/android/bsp-log-evidence-manifest.json":
        raise AssertionError("android sim report must reference the BSP log evidence manifest")
    required = data.get("required_evidence", [])
    for path in (
        "docs/evidence/android/openphone_ai_soc_sepolicy_build.log",
        "docs/evidence/android/openphone_ai_soc_cts_vts_plan.log",
        "docs/evidence/android/qemu_riscv64_smoke.log",
        "docs/evidence/android/renode_hello_soc_smoke.log",
    ):
        if path not in required:
            raise AssertionError(f"android sim report missing required evidence category {path}")


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
    assert_contains(result.stdout, "/dev/kvm")
    assert_contains(result.stdout, "Cuttlefish launcher")


def test_checker_rejects_pass_without_required_aosp_evidence() -> None:
    blocked = json.loads(REPORT.read_text()) if REPORT.is_file() else None
    if blocked is None or blocked.get("status") != "blocked":
        test_boot_script_blocks_without_aosp_dir()
        blocked = json.loads(REPORT.read_text())
    blocked["status"] = "pass"
    blocked["reason"] = "synthetic pass report for checker coverage"
    blocked["next_step"] = "none"
    REPORT.write_text(json.dumps(blocked, indent=2))
    result = run([sys.executable, str(CHECK)])
    if result.returncode != 1:
        raise AssertionError(
            f"expected checker to reject pass without evidence, got {result.returncode}\n{result.stdout}"
        )
    assert_contains(result.stdout, "Android simulator boot failed")
    assert_contains(result.stdout, "pass report")


def test_aosp_linux_preflight_blocks_without_aosp_dir() -> None:
    saved = PREFLIGHT_REPORT.read_bytes() if PREFLIGHT_REPORT.is_file() else None
    try:
        result = run([sys.executable, str(PREFLIGHT), "--json", "--write-report"])
        if result.returncode != 2:
            raise AssertionError(
                f"expected preflight to block, got {result.returncode}\n{result.stdout}"
            )
        data = json.loads(result.stdout)
        if data.get("schema") != "openphone.aosp_linux_preflight.v1":
            raise AssertionError("AOSP Linux preflight schema mismatch")
        if data.get("status") != "blocked":
            raise AssertionError("AOSP Linux preflight must block without AOSP_DIR")
        if "AOSP_DIR is not set" not in data.get("blockers", []):
            raise AssertionError("AOSP Linux preflight must report missing AOSP_DIR")
        if data.get("claim_boundary") != (
            "host_preflight_only_not_aosp_build_boot_cuttlefish_or_hello_chip_hardware_evidence"
        ):
            raise AssertionError("AOSP Linux preflight claim boundary changed")
        if "does not create docs/evidence/android logs" not in data.get("evidence_policy", ""):
            raise AssertionError("AOSP Linux preflight must not fabricate evidence logs")
    finally:
        if saved is None:
            PREFLIGHT_REPORT.unlink(missing_ok=True)
        else:
            PREFLIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
            PREFLIGHT_REPORT.write_bytes(saved)


def main() -> int:
    saved = REPORT.read_bytes() if REPORT.is_file() else None
    try:
        for test in (
            test_boot_script_blocks_without_aosp_dir,
            test_checker_reports_blocked_report,
            test_checker_rejects_pass_without_required_aosp_evidence,
            test_aosp_linux_preflight_blocks_without_aosp_dir,
        ):
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
