#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/mvp_simulator.json"

STEPS = [
    {
        "name": "android_sim_boot",
        "tier": "os_boot",
        "claim": "Android simulator boot evidence",
        "command": [
            "scripts/boot_android_simulator.sh",
            "--run-cuttlefish",
            "--run-cts",
            "--run-vts",
        ],
        "pass_markers": ["PASS: Android simulator evidence captured and validated"],
        "block_markers": ["BLOCKED:"],
    },
    {
        "name": "android_sim_report_check",
        "tier": "os_boot",
        "claim": "validated Android simulator boot report",
        "command": [sys.executable, "scripts/check_android_sim_boot.py"],
        "pass_markers": ["Android simulator boot check passed"],
        "block_markers": ["Android simulator boot blocked"],
    },
    {
        "name": "qemu_os_boot",
        "tier": "os_boot",
        "claim": "QEMU OS boot to init/login",
        "command": ["scripts/run_qemu.sh", "--check-os"],
        "pass_markers": ["STATUS: PASS qemu.os_boot"],
        "block_markers": ["STATUS: BLOCKED qemu.os_boot"],
    },
    {
        "name": "cpu_ap_linux_evidence",
        "tier": "os_prereq",
        "claim": "CPU/AP Linux evidence prerequisites",
        "command": [sys.executable, "scripts/check_cpu_ap_evidence.py", "--require-evidence"],
        "pass_markers": ["STATUS: PASS cpu_ap.linux_evidence"],
        "block_markers": ["STATUS: BLOCKED cpu_ap.linux_evidence"],
    },
    {
        "name": "chipyard_generated_ap",
        "tier": "os_prereq",
        "claim": "generated CPU/AP simulator input",
        "command": [
            sys.executable,
            "scripts/check_chipyard_generator_manifest.py",
            "--require-generated",
        ],
        "pass_markers": ["STATUS: PASS chipyard.generated_import"],
        "block_markers": ["STATUS: BLOCKED chipyard.generated_import"],
    },
    {
        "name": "chipyard_verilator_preflight",
        "tier": "os_prereq",
        "claim": "Chipyard Verilator environment can generate OpenPhoneRocketConfig",
        "command": [sys.executable, "scripts/check_chipyard_verilator_preflight.py"],
        "pass_markers": ["STATUS: PASS chipyard.verilator_preflight"],
        "block_markers": ["STATUS: BLOCKED chipyard.verilator_preflight"],
    },
    {
        "name": "qemu_firmware_smoke",
        "tier": "firmware_smoke",
        "claim": "QEMU qemu-virt firmware serial smoke",
        "command": ["scripts/run_qemu.sh", "--check"],
        "pass_markers": ["STATUS: PASS qemu.check"],
        "block_markers": ["STATUS: BLOCKED qemu.check"],
    },
    {
        "name": "renode_firmware_smoke",
        "tier": "firmware_smoke",
        "claim": "Renode qemu-virt firmware serial smoke",
        "command": ["scripts/run_renode.sh", "--check"],
        "pass_markers": ["STATUS: PASS renode.check"],
        "block_markers": ["STATUS: BLOCKED renode.check"],
    },
    {
        "name": "local_rtl_sim_ladder",
        "tier": "rtl_sim",
        "claim": "local RTL simulation ladder",
        "command": [sys.executable, "scripts/run_sim_ladder.py"],
        "pass_markers": ["Simulation ladder passed"],
        "block_markers": [],
    },
]

TIER_RANK = {
    "os_boot": 4,
    "os_prereq": 3,
    "firmware_smoke": 2,
    "rtl_sim": 1,
}


def classify(returncode: int, output: str, step: dict[str, Any]) -> str:
    pass_markers = step["pass_markers"]
    block_markers = step["block_markers"]
    assert isinstance(pass_markers, list)
    assert isinstance(block_markers, list)
    if returncode == 0 and all(
        isinstance(marker, str) and marker in output for marker in pass_markers
    ):
        return "pass"
    if returncode == 2 or any(
        isinstance(marker, str) and marker in output for marker in block_markers
    ):
        return "blocked"
    return "fail"


def run_step(step: dict[str, Any]) -> dict[str, Any]:
    command = step["command"]
    assert isinstance(command, list)
    start = time.time()
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = round(time.time() - start, 3)
    status = classify(result.returncode, result.stdout, step)
    return {
        "name": step["name"],
        "tier": step["tier"],
        "claim": step["claim"],
        "command": command,
        "status": status,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "log_tail": result.stdout.splitlines()[-40:],
    }


def best_executable_evidence(results: list[dict[str, object]]) -> dict[str, object] | None:
    passing = [item for item in results if item.get("status") == "pass"]
    if not passing:
        return None
    return max(passing, key=lambda item: TIER_RANK.get(str(item.get("tier")), 0))


def blocked_items(results: list[dict[str, object]]) -> list[dict[str, object]]:
    items = []
    for item in results:
        if item.get("status") != "blocked":
            continue
        tail = item.get("log_tail", [])
        detail = ""
        if isinstance(tail, list) and tail:
            detail = str(tail[-1])
        command = item.get("command", [])
        if not isinstance(command, list):
            command = []
        items.append(
            {
                "name": item.get("name"),
                "tier": item.get("tier"),
                "detail": detail,
                "next_command": " ".join(str(part) for part in command),
            }
        )
    return items


def failed_items(results: list[dict[str, object]]) -> list[dict[str, object]]:
    items = []
    for item in results:
        if item.get("status") != "fail":
            continue
        command = item.get("command", [])
        if not isinstance(command, list):
            command = []
        items.append(
            {
                "name": item.get("name"),
                "tier": item.get("tier"),
                "next_command": " ".join(str(part) for part in command),
            }
        )
    return items


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for step in STEPS:
        item = run_step(step)
        results.append(item)

    statuses = {item["status"] for item in results}
    if "fail" in statuses:
        overall = "fail"
        code = 1
    elif "blocked" in statuses or len(results) != len(STEPS):
        overall = "blocked"
        code = 2
    else:
        overall = "pass"
        code = 0

    best = best_executable_evidence(results)
    os_boot_passed = any(
        item.get("tier") == "os_boot" and item.get("status") == "pass" for item in results
    )

    report = {
        "schema": "openphone.mvp_simulator.v1",
        "status": overall,
        "strongest_attempted": "os_boot",
        "best_executable_evidence": best["name"] if best else "none",
        "best_executable_tier": best["tier"] if best else "none",
        "os_boot_claim": bool(os_boot_passed),
        "remaining_blockers": blocked_items(results),
        "failures": failed_items(results),
        "claim_boundary": "Simulator MVP tries OS boot first, then OS prerequisites, firmware smoke, and RTL sim evidence. OS boot may be claimed only when an executable boot reaches init/login or validated Android boot evidence passes. It is not a fabrication or phone-class performance claim.",
        "results": results,
    }
    tmp = REPORT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    tmp.replace(REPORT)

    print(f"MVP simulator {overall}; wrote {REPORT.relative_to(ROOT)}")
    print(f"  strongest_attempted: {report['strongest_attempted']}")
    print(
        f"  best_executable_evidence: {report['best_executable_evidence']} "
        f"({report['best_executable_tier']})"
    )
    print(f"  os_boot_claim: {str(report['os_boot_claim']).lower()}")
    for item in results:
        print(f"  - {item['name']}: {item['status']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
