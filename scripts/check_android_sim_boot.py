#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/android_sim_boot.json"
MANIFEST = ROOT / "sw/aosp-device/evidence_manifest.json"
REFERENCE_ONLY_BOUNDARY = "reference_only_not_hello_chip_ap_evidence"
REFERENCE_ONLY_EVIDENCE = {
    "docs/evidence/android/cuttlefish_riscv64_boot.log",
    "docs/evidence/android/cts_virtual_device_subset.log",
    "docs/evidence/android/vts_virtual_device_subset.log",
}

VALID_STATUSES = {"pass", "blocked", "failed"}
REQUIRED_REPORT_FIELDS = {
    "schema": str,
    "status": str,
    "reason": str,
    "next_step": str,
    "aosp_dir": str,
    "run_cuttlefish": bool,
    "run_cts": bool,
    "run_vts": bool,
    "require_full_evidence": bool,
    "host_requirements": dict,
    "claim_boundary": str,
}


def main() -> int:
    errors: list[str] = []
    if not MANIFEST.is_file():
        return report("failed", [f"missing {MANIFEST.relative_to(ROOT)}"])
    try:
        manifest = json.loads(MANIFEST.read_text())
    except json.JSONDecodeError as exc:
        return report("failed", [f"{MANIFEST.relative_to(ROOT)} is invalid JSON: {exc}"])

    if manifest.get("android_boot_claim") != "blocked_until_all_required_evidence_passes":
        errors.append("AOSP evidence manifest must keep Android boot claims blocked by default")
    required_evidence = manifest.get("required_for_android_boot_claim")
    if not isinstance(required_evidence, list) or not required_evidence:
        errors.append("AOSP evidence manifest must list required boot evidence")

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
    boundary = data.get("claim_boundary", "")
    if "not hello-chip hardware ABI proof" not in boundary:
        errors.append(
            "android sim report must separate Cuttlefish/qemu-virt from hello-chip ABI proof"
        )
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
        for path in required_evidence or []:
            evidence = ROOT / path
            if not evidence.is_file() or evidence.stat().st_size == 0:
                errors.append(f"pass report is missing required evidence {path}")
            elif "openphone-evidence: status=PASS" not in evidence.read_text(errors="ignore"):
                errors.append(f"required evidence {path} does not record PASS")
            elif path in REFERENCE_ONLY_EVIDENCE:
                text = evidence.read_text(errors="ignore")
                marker = f"openphone-evidence: claim_boundary={REFERENCE_ONLY_BOUNDARY}"
                if marker not in text:
                    errors.append(f"required reference-only evidence {path} is missing {marker}")

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
