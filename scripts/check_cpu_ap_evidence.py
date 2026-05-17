#!/usr/bin/env python3
"""Separate CPU/AP scaffold checks from Linux-capable evidence claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_scaffold(errors: list[str]) -> None:
    cpu = read("rtl/cpu/hello_cpu_subsystem_stub.sv")
    test = read("verify/cocotb/test_tiny_cpu_execution.py")
    tb = read("verify/cocotb/hello_tiny_cpu_contract_tb.sv")
    linux_contract = read("docs/arch/linux-capable-cpu-contract.md")
    blocker = read("docs/project/cpu-ap-blocker-status-2026-05-17.md")
    contract = json.loads(read("sw/platform/hello_platform_contract.json"))

    require("FETCH_REQ" in cpu and "EXECUTE" in cpu, "tiny CPU no longer has fetch/execute states", errors)
    require("7'b0010011" in cpu and "7'b0000011" in cpu, "tiny CPU opcode subset drifted", errors)
    require("irq_pending = timer_irq | software_irq | external_irq" in cpu, "IRQ placeholder reflection changed", errors)
    require("stall_cpu_ar" in tb and "stall_cpu_aw" in tb and "stall_cpu_w" in tb, "CPU contract TB lacks request stall injection", errors)
    require("tiny_cpu_extended_opcode_subset_has_observable_state" in test, "tiny CPU opcode coverage test is missing", errors)
    require("tiny_cpu_waits_for_fetch_and_store_request_stalls" in test, "tiny CPU bus stall test is missing", errors)
    require(
        "tiny_cpu_privileged_csr_and_trap_instructions_are_blocked_scaffold" in test,
        "tiny CPU privileged/CSR/trap-class fail-closed test is missing",
        errors,
    )
    require(
        contract["hello_chip"].get("has_cpu") is False,
        "platform contract must remain has_cpu=false until package top integrates a production CPU",
        errors,
    )
    require(
        (ROOT / "docs/arch/linux-capable-cpu-contract.md").is_file(),
        "Linux-capable CPU requirements gate is missing",
        errors,
    )
    for token in (
        "OpenSBI",
        "Linux early console",
        "mcause",
        "mepc",
        "mtimecmp",
        "external interrupt claim/complete",
        "firmware-to-kernel handoff",
    ):
        require(token in linux_contract, f"Linux-capable CPU contract lacks required evidence token: {token}", errors)
    for token in (
        "No generated Chipyard/Rocket RTL",
        "OpenSBI plus Linux early console",
        "has_cpu=false",
    ):
        require(token in blocker, f"CPU/AP blocker status lacks required blocker token: {token}", errors)


def missing_evidence() -> list[str]:
    required = (
        "build/evidence/cpu_ap/openphone_hello_opensbi_boot.log",
        "build/evidence/cpu_ap/openphone_hello_linux_boot.log",
        "build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log",
    )
    return [path for path in required if not (ROOT / path).is_file()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    check_scaffold(errors)
    if errors:
        print("CPU/AP scaffold check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("STATUS: PASS cpu_ap.scaffold - tiny executable CPU path and gates are present")
    absent = missing_evidence()
    if absent:
        print("STATUS: BLOCKED cpu_ap.linux_evidence - missing production boot/trap evidence:")
        for path in absent:
            print(f"  - {path}")
        return 1 if args.require_evidence else 0

    print("STATUS: PASS cpu_ap.linux_evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
