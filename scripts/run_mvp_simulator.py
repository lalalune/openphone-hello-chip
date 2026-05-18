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
        "scope": "android_reference",
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
        "scope": "android_reference",
        "claim": "validated Android simulator boot report",
        "command": [sys.executable, "scripts/check_android_sim_boot.py"],
        "pass_markers": ["Android simulator boot check passed"],
        "block_markers": ["Android simulator boot blocked"],
    },
    {
        "name": "qemu_os_boot",
        "tier": "os_boot",
        "scope": "qemu_virt_reference",
        "claim": "QEMU qemu-virt reference OS boot to init/login; not hello-chip/AP evidence",
        "command": ["scripts/run_qemu.sh", "--check-os"],
        "pass_markers": ["STATUS: PASS qemu.os_boot"],
        "block_markers": ["STATUS: BLOCKED qemu.os_boot"],
    },
    {
        "name": "cpu_ap_linux_evidence",
        "tier": "os_prereq",
        "scope": "our_chip_prereq",
        "claim": "CPU/AP Linux evidence prerequisites",
        "command": [sys.executable, "scripts/check_cpu_ap_evidence.py", "--require-evidence"],
        "pass_markers": ["STATUS: PASS cpu_ap.linux_evidence"],
        "block_markers": ["STATUS: BLOCKED cpu_ap.linux_evidence"],
    },
    {
        "name": "chipyard_verilator_preflight",
        "tier": "os_prereq",
        "scope": "our_chip_prereq",
        "claim": "Chipyard Verilator environment can generate OpenPhoneRocketConfig",
        "command": [sys.executable, "scripts/check_chipyard_verilator_preflight.py"],
        "pass_markers": ["STATUS: PASS chipyard.verilator_preflight"],
        "block_markers": ["STATUS: BLOCKED chipyard.verilator_preflight"],
    },
    {
        "name": "chipyard_generated_ap",
        "tier": "os_prereq",
        "scope": "our_chip_prereq",
        "claim": "generated CPU/AP simulator input",
        "command": [
            sys.executable,
            "scripts/check_chipyard_generator_manifest.py",
            "--require-generated",
        ],
        "pass_markers": ["STATUS: PASS chipyard.generated_import"],
        "block_markers": [
            "STATUS: BLOCKED chipyard.generated_import",
            "Verilator preflight blocker:",
            "missing generated import manifest:",
        ],
    },
    {
        "name": "chipyard_payload_path",
        "tier": "os_prereq",
        "scope": "our_chip_prereq",
        "claim": "generated Chipyard DTS/artifacts are ready for the external OpenSBI/U-Boot/Linux payload path; not RTL boot evidence",
        "command": [sys.executable, "scripts/check_chipyard_payload_path.py"],
        "pass_markers": ["STATUS: PASS chipyard.payload_path"],
        "block_markers": ["STATUS: BLOCKED chipyard.payload_path"],
    },
    {
        "name": "chipyard_verilator_linux_smoke",
        "tier": "os_boot",
        "scope": "our_chip_os_boot",
        "claim": "OpenSBI/Linux smoke on generated OpenPhoneRocketConfig Verilator simulator",
        "command": [sys.executable, "scripts/check_chipyard_verilator_linux_smoke.py"],
        "pass_markers": ["STATUS: PASS chipyard.verilator_linux_smoke"],
        "block_markers": ["STATUS: BLOCKED chipyard.verilator_linux_smoke"],
    },
    {
        "name": "qemu_firmware_smoke",
        "tier": "firmware_smoke",
        "scope": "qemu_virt_reference",
        "claim": "QEMU qemu-virt firmware serial smoke",
        "command": ["scripts/run_qemu.sh", "--check"],
        "pass_markers": ["STATUS: PASS qemu.check"],
        "block_markers": ["STATUS: BLOCKED qemu.check"],
    },
    {
        "name": "renode_firmware_smoke",
        "tier": "firmware_smoke",
        "scope": "renode_reference",
        "claim": "Renode firmware serial smoke on the current Renode reference model; not generated AP/Linux evidence",
        "command": ["scripts/run_renode.sh", "--check"],
        "pass_markers": ["STATUS: PASS renode.check"],
        "block_markers": ["STATUS: BLOCKED renode.check"],
    },
    {
        "name": "local_rtl_sim_ladder",
        "tier": "rtl_sim",
        "scope": "our_chip_rtl_sim",
        "claim": "local RTL simulation ladder",
        "command": [sys.executable, "scripts/run_sim_ladder.py"],
        "pass_markers": ["Simulation ladder passed"],
        "block_markers": ["STATUS: BLOCKED sim_ladder"],
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
        "scope": step["scope"],
        "claim": step["claim"],
        "command": command,
        "status": status,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "log_tail": result.stdout.splitlines()[-40:],
    }


def best_executable_evidence(results: list[dict[str, object]]) -> dict[str, object] | None:
    passing = [
        item
        for item in results
        if item.get("status") == "pass"
        and item.get("scope") in {"our_chip_prereq", "our_chip_os_boot", "our_chip_rtl_sim"}
    ]
    if not passing:
        return None
    return max(passing, key=lambda item: TIER_RANK.get(str(item.get("tier")), 0))


def best_reference_evidence(results: list[dict[str, object]]) -> dict[str, object] | None:
    passing = [
        item
        for item in results
        if item.get("status") == "pass"
        and item.get("scope") in {"qemu_virt_reference", "renode_reference", "android_reference"}
    ]
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
            status_lines = [
                str(line)
                for line in tail
                if str(line).startswith("STATUS: BLOCKED ") or str(line).startswith("BLOCKED:")
            ]
            detail = status_lines[-1] if status_lines else str(tail[-1])
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
        tail = item.get("log_tail", [])
        detail = ""
        if isinstance(tail, list) and tail:
            status_lines = [
                str(line)
                for line in tail
                if str(line).startswith("STATUS: FAIL ") or str(line).startswith("FAIL:")
            ]
            detail = status_lines[-1] if status_lines else str(tail[-1])
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
    best_reference = best_reference_evidence(results)
    qemu_reference_os_boot_passed = any(
        item.get("name") == "qemu_os_boot" and item.get("status") == "pass" for item in results
    )
    android_reference_os_boot_passed = any(
        item.get("scope") == "android_reference" and item.get("status") == "pass"
        for item in results
    )
    on_chip_os_boot_passed = any(
        item.get("scope") == "our_chip_os_boot" and item.get("status") == "pass" for item in results
    )
    on_chip_blockers = [
        item
        for item in blocked_items(results)
        if any(
            result.get("name") == item.get("name")
            and result.get("scope") in {"our_chip_prereq", "our_chip_os_boot"}
            for result in results
        )
    ]

    report = {
        "schema": "openphone.mvp_simulator.v1",
        "status": overall,
        "strongest_attempted": "os_boot",
        "best_executable_evidence": best["name"] if best else "none",
        "best_executable_tier": best["tier"] if best else "none",
        "best_reference_evidence": best_reference["name"] if best_reference else "none",
        "best_reference_tier": best_reference["tier"] if best_reference else "none",
        "os_boot_claim": bool(on_chip_os_boot_passed),
        "on_chip_os_boot_claim": bool(on_chip_os_boot_passed),
        "reference_qemu_virt_os_boot_claim": bool(qemu_reference_os_boot_passed),
        "reference_android_os_boot_claim": bool(android_reference_os_boot_passed),
        "qemu_virt_reference_only": True,
        "renode_reference_only": True,
        "blockers_to_on_chip_os_boot": on_chip_blockers,
        "remaining_blockers": blocked_items(results),
        "failures": failed_items(results),
        "claim_boundary": "Simulator MVP separates qemu-virt/Renode/Android reference evidence from OS running on generated OpenPhone AP/hello-chip RTL. qemu_os_boot may be claimed only as reference_qemu_virt_os_boot_claim. Renode smoke is renode_reference_only unless a generated hello-chip hardware model and transcript are archived. OS on our chip may be claimed only when on_chip_os_boot_claim is true from generated AP/Linux evidence; qemu-virt, Renode, and Android simulator evidence do not satisfy that claim. It is not a fabrication or phone-class performance claim.",
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
    print(
        f"  best_reference_evidence: {report['best_reference_evidence']} "
        f"({report['best_reference_tier']})"
    )
    print(
        f"  reference_qemu_virt_os_boot_claim: {str(report['reference_qemu_virt_os_boot_claim']).lower()}"
    )
    print(f"  on_chip_os_boot_claim: {str(report['on_chip_os_boot_claim']).lower()}")
    for item in results:
        print(f"  - {item['name']}: {item['status']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
