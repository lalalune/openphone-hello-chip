#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/mvp_simulator.json"
REQUIRED_STEPS = {
    "local_rtl_sim_ladder",
    "chipyard_generated_ap",
    "qemu_firmware_smoke",
    "renode_firmware_smoke",
    "qemu_os_boot",
    "cpu_ap_linux_evidence",
    "chipyard_verilator_preflight",
    "android_sim_boot",
    "android_sim_report_check",
}


def main() -> int:
    if not REPORT.is_file():
        print(f"MVP simulator check blocked: missing {REPORT.relative_to(ROOT)}")
        print("Next step: python3 scripts/run_mvp_simulator.py")
        return 2
    try:
        data = json.loads(REPORT.read_text())
    except json.JSONDecodeError as exc:
        print(f"MVP simulator check failed: invalid JSON report: {exc}")
        return 1

    errors: list[str] = []
    if data.get("schema") != "openphone.mvp_simulator.v1":
        errors.append("schema mismatch")
    boundary = data.get("claim_boundary", "")
    if "not a fabrication or phone-class performance claim" not in boundary:
        errors.append(
            "claim boundary must separate simulator MVP from fabrication/performance claims"
        )
    if "OS boot may be claimed only" not in boundary:
        errors.append("claim boundary must restrict OS boot claims to executable boot evidence")
    if data.get("strongest_attempted") != "os_boot":
        errors.append("strongest_attempted must record os_boot")
    if not isinstance(data.get("os_boot_claim"), bool):
        errors.append("os_boot_claim must be bool")
    if not isinstance(data.get("best_executable_evidence"), str):
        errors.append("best_executable_evidence must be string")
    if data.get("best_executable_tier") not in {
        "os_boot",
        "os_prereq",
        "firmware_smoke",
        "rtl_sim",
        "none",
    }:
        errors.append("best_executable_tier is invalid")
    if not isinstance(data.get("remaining_blockers"), list):
        errors.append("remaining_blockers must be list")
    if not isinstance(data.get("failures"), list):
        errors.append("failures must be list")

    results = data.get("results")
    if not isinstance(results, list) or not results:
        errors.append("results must be a non-empty list")
        results = []
    seen = {item.get("name") for item in results if isinstance(item, dict)}
    missing = sorted(REQUIRED_STEPS - seen)
    if missing and data.get("status") == "pass":
        errors.append("pass report missing required steps: " + ", ".join(missing))
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"results[{index}] must be an object")
            continue
        if item.get("status") not in {"pass", "blocked", "fail"}:
            errors.append(f"results[{index}] status is invalid")
        if item.get("tier") not in {"os_boot", "os_prereq", "firmware_smoke", "rtl_sim"}:
            errors.append(f"results[{index}] tier is invalid")
        if not isinstance(item.get("claim"), str) or not item["claim"]:
            errors.append(f"results[{index}] claim must be non-empty string")
        if not isinstance(item.get("command"), list) or not item["command"]:
            errors.append(f"results[{index}] command must be a non-empty list")
        if not isinstance(item.get("returncode"), int):
            errors.append(f"results[{index}] returncode must be int")
    if data.get("os_boot_claim") is True and not any(
        isinstance(item, dict) and item.get("tier") == "os_boot" and item.get("status") == "pass"
        for item in results
    ):
        errors.append("os_boot_claim true without passing OS boot result")

    if errors:
        print("MVP simulator check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    status = data.get("status")
    if status == "pass":
        print("MVP simulator check passed")
        return 0
    if status == "blocked":
        print("MVP simulator check blocked")
        for item in results:
            if item.get("status") == "blocked":
                print(f"  - {item.get('name')}: blocked")
        return 2
    print("MVP simulator check failed")
    for item in results:
        if item.get("status") == "fail":
            print(f"  - {item.get('name')}: failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
