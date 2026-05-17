#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/android_sim_boot.json"
LOG_EVIDENCE_MANIFEST = ROOT / "docs/android/bsp-log-evidence-manifest.json"

sys.path.insert(0, str(ROOT / "scripts"))
import check_software_bsp  # noqa: E402

VALID_STATUSES = {"pass", "blocked", "failed"}
REQUIRED_REPORT_FIELDS = {
    "schema": str,
    "status": str,
    "reason": str,
    "next_step": str,
    "aosp_dir": str,
    "aosp_product": str,
    "run_cuttlefish": bool,
    "run_cts": bool,
    "run_vts": bool,
    "run_qemu": bool,
    "run_renode": bool,
    "require_full_evidence": bool,
    "evidence_manifest": str,
    "software_bsp_checker": str,
    "required_evidence": list,
    "attempted_evidence": list,
    "host_requirements": dict,
    "claim_boundary": str,
}


def main() -> int:
    errors: list[str] = []
    required_evidence = check_software_bsp.TARGETS["aosp"]["evidence"]
    build_only_evidence = [
        path
        for path in required_evidence
        if path
        not in {
            "docs/evidence/android/openphone_ai_soc_cts_vts_plan.log",
            "docs/evidence/android/cuttlefish_riscv64_smoke.log",
            "docs/evidence/android/qemu_riscv64_smoke.log",
            "docs/evidence/android/renode_hello_soc_smoke.log",
        }
    ]
    if not LOG_EVIDENCE_MANIFEST.is_file():
        return report("failed", [f"missing {LOG_EVIDENCE_MANIFEST.relative_to(ROOT)}"])
    try:
        manifest = json.loads(LOG_EVIDENCE_MANIFEST.read_text())
    except json.JSONDecodeError as exc:
        return report(
            "failed", [f"{LOG_EVIDENCE_MANIFEST.relative_to(ROOT)} is invalid JSON: {exc}"]
        )

    if manifest.get("claim_boundary") != "expected_future_log_markers_only_not_boot_evidence":
        errors.append("AOSP log evidence manifest must keep the expected-future-log boundary")
    manifest_logs = manifest.get("logs", {})
    if not isinstance(manifest_logs, dict):
        errors.append("AOSP log evidence manifest logs must be an object")
        manifest_logs = {}
    missing_manifest_specs = [path for path in required_evidence if path not in manifest_logs]
    if missing_manifest_specs:
        errors.append(
            "AOSP log evidence manifest missing required specs: "
            + ", ".join(missing_manifest_specs)
        )

    if not REPORT.is_file():
        return report(
            "blocked",
            errors
            + [
                f"missing {REPORT.relative_to(ROOT)}",
                "run scripts/boot_android_simulator.sh with AOSP_DIR set",
            ],
        )

    try:
        data = json.loads(REPORT.read_text())
    except json.JSONDecodeError as exc:
        return report("failed", errors + [f"{REPORT.relative_to(ROOT)} is invalid JSON: {exc}"])

    for field, expected_type in REQUIRED_REPORT_FIELDS.items():
        value = data.get(field)
        if not isinstance(value, expected_type):
            errors.append(f"android sim report {field} must be {expected_type.__name__}")

    if data.get("schema") != "openphone.android_sim_boot.v1":
        errors.append("android sim report schema mismatch")
    status = data.get("status")
    if status not in VALID_STATUSES:
        errors.append(f"android sim report status {status!r} is invalid")
    if data.get("evidence_manifest") != "docs/android/bsp-log-evidence-manifest.json":
        errors.append(
            "android sim report must reference docs/android/bsp-log-evidence-manifest.json"
        )
    if data.get("software_bsp_checker") != "scripts/check_software_bsp.py aosp --require-evidence":
        errors.append("android sim report must reference the strict AOSP BSP evidence checker")
    if data.get("required_evidence") != required_evidence:
        errors.append("android sim report required_evidence must match check_software_bsp.py aosp")
    attempted = data.get("attempted_evidence")
    if data.get("require_full_evidence") is True and attempted != required_evidence:
        errors.append("full android sim report must attempt every required AOSP evidence category")
    if data.get("require_full_evidence") is False and attempted != build_only_evidence:
        errors.append(
            "build-only android sim report must stop before virtual-device smoke and compatibility evidence"
        )
    boundary = data.get("claim_boundary", "")
    if "not hello-chip hardware ABI proof" not in boundary:
        errors.append(
            "android sim report must separate Android virtual-device evidence from hello-chip ABI proof"
        )
    if "compatibility claim" not in boundary:
        errors.append("android sim report must avoid full Android compatibility claims")
    host_requirements = data.get("host_requirements", {})
    if isinstance(host_requirements, dict):
        if not isinstance(host_requirements.get("host_os"), str):
            errors.append("android sim report host_requirements.host_os must be string")
        if not isinstance(host_requirements.get("host_arch"), str):
            errors.append("android sim report host_requirements.host_arch must be string")
        missing = host_requirements.get("missing")
        if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
            errors.append("android sim report host_requirements.missing must be a string list")

    if status == "pass":
        bsp_report = check_software_bsp.target_report("aosp")
        if bsp_report["errors"]:
            errors.extend(f"AOSP BSP evidence error: {error}" for error in bsp_report["errors"])
        missing_evidence = bsp_report["missing_evidence"]
        if missing_evidence:
            errors.extend(
                f"pass report is missing required evidence {item['path']}({item['blocker_code']})"
                for item in missing_evidence
            )
        if bsp_report["evidence_status"] != "PASS":
            errors.append(
                f"pass report cannot clear while AOSP evidence_status={bsp_report['evidence_status']}"
            )
    elif status == "blocked" and data.get("require_full_evidence") is False:
        attempted_paths = data.get("attempted_evidence", [])
        forbidden_build_only = sorted(set(attempted_paths) - set(build_only_evidence))
        if forbidden_build_only:
            errors.append(
                "build-only blocked report attempted virtual-device or compatibility evidence: "
                + ", ".join(forbidden_build_only)
            )

    if errors:
        severity = "blocked" if status == "blocked" else "failed"
        return report(severity, errors)

    if status == "pass":
        print("Android simulator boot check passed")
        return 0

    print(f"Android simulator boot blocked: {data.get('reason')}")
    print(f"Next step: {data.get('next_step')}")
    return 2


def report(status: str, errors: list[str]) -> int:
    code = 2 if status == "blocked" else 1
    heading = (
        "Android simulator boot blocked" if status == "blocked" else "Android simulator boot failed"
    )
    print(f"{heading}:")
    for error in errors:
        print(f"  - {error}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
