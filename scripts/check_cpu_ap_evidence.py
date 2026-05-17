#!/usr/bin/env python3
"""Separate CPU/AP scaffold checks from Linux-capable evidence claims."""

from __future__ import annotations

import argparse

from cpu_ap_evidence_lib import (
    EXPECTED_CHIPYARD,
    ROOT,
    SELECTED_MANIFEST,
    load_evidence_manifest,
    load_json,
    require,
    text_problems,
    transcript_specs,
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def check_scaffold(errors: list[str]) -> None:
    evidence_manifest = load_evidence_manifest(errors)
    cpu = read("rtl/cpu/hello_cpu_subsystem_stub.sv")
    test = read("verify/cocotb/test_tiny_cpu_execution.py")
    tb = read("verify/cocotb/hello_tiny_cpu_contract_tb.sv")
    linux_contract = read("docs/arch/linux-capable-cpu-contract.md")
    blocker = read("docs/project/cpu-ap-blocker-status-2026-05-17.md")
    contract = load_json(ROOT / "sw/platform/hello_platform_contract.json")
    manifest = load_json(SELECTED_MANIFEST)
    chipyard = manifest.get("chipyard", {})
    selected = manifest.get("selected_path", {})
    claim_policy = manifest.get("claim_policy", {})

    require(
        "FETCH_REQ" in cpu and "EXECUTE" in cpu,
        "tiny CPU no longer has fetch/execute states",
        errors,
    )
    require("7'b0010011" in cpu and "7'b0000011" in cpu, "tiny CPU opcode subset drifted", errors)
    require(
        "irq_pending = timer_irq | software_irq | external_irq" in cpu,
        "IRQ placeholder reflection changed",
        errors,
    )
    require(
        "stall_cpu_ar" in tb and "stall_cpu_aw" in tb and "stall_cpu_w" in tb,
        "CPU contract TB lacks request stall injection",
        errors,
    )
    require(
        "tiny_cpu_extended_opcode_subset_has_observable_state" in test,
        "tiny CPU opcode coverage test is missing",
        errors,
    )
    require(
        "tiny_cpu_waits_for_fetch_and_store_request_stalls" in test,
        "tiny CPU bus stall test is missing",
        errors,
    )
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
        manifest.get("status") == "selected_not_generated",
        "Rocket manifest must not claim generated artifacts yet",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"],
        "Chipyard AP path must remain pinned to tag 1.13.0",
        errors,
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
        "Chipyard AP path must remain pinned to the selected commit",
        errors,
    )
    require(
        selected.get("core") == "Rocket" and selected.get("isa") == "RV64GC",
        "AP path must select Rocket RV64GC",
        errors,
    )
    require(
        selected.get("harts") == 1,
        "first local AP integration target must remain single-hart",
        errors,
    )
    require(
        selected.get("config_name") == "OpenPhoneRocketConfig",
        "AP config name drifted",
        errors,
    )
    require(
        claim_policy.get("linux_capable_cpu_claim") is False,
        "manifest must not claim Linux boot without evidence",
        errors,
    )
    require(
        manifest.get("evidence_manifest") == "docs/evidence/cpu-ap-evidence-manifest.json",
        "selected manifest must point to CPU/AP evidence manifest",
        errors,
    )
    require(
        manifest.get("capture_helper") == "scripts/capture_cpu_ap_evidence.py",
        "selected manifest must point to CPU/AP evidence capture helper",
        errors,
    )
    for spec in transcript_specs(evidence_manifest).values():
        path = spec.get("path")
        require(
            path in manifest.get("required_evidence", []),
            f"selected manifest lacks required CPU/AP evidence path: {path}",
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
        require(
            token in linux_contract,
            f"Linux-capable CPU contract lacks required evidence token: {token}",
            errors,
        )
    for token in (
        "No generated Chipyard/Rocket RTL",
        "OpenPhoneRocketConfig",
        "has_cpu=false",
    ):
        require(
            token in blocker,
            f"CPU/AP blocker status lacks required blocker token: {token}",
            errors,
        )


def evidence_problems() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    evidence_manifest = load_evidence_manifest(errors)
    missing: list[str] = []
    problems = errors[:]
    for spec in transcript_specs(evidence_manifest).values():
        rel_path = spec.get("path")
        if not isinstance(rel_path, str):
            continue
        path = ROOT / rel_path
        if not path.is_file():
            missing.append(rel_path)
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        problems.extend(text_problems(text, spec, rel_path, raw=False))
    return missing, problems


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
    absent, problems = evidence_problems()
    if problems:
        print("STATUS: FAIL cpu_ap.linux_evidence - evidence logs are invalid:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    if absent:
        print("STATUS: BLOCKED cpu_ap.linux_evidence - missing production boot/trap evidence:")
        for path in absent:
            print(f"  - {path}")
        print("  next: python3 scripts/capture_cpu_ap_evidence.py --help")
        return 1 if args.require_evidence else 0

    print("STATUS: PASS cpu_ap.linux_evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
