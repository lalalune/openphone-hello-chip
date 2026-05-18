#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "sw/platform/hello_platform_contract.json"
MEMORY_MAP = ROOT / "docs/arch/memory-map.md"
MEMORY_SUBSYSTEM = ROOT / "docs/arch/memory-subsystem.md"
INTERCONNECT = ROOT / "docs/arch/interconnect.md"
UMA = ROOT / "docs/project/uma-coherency-validation-strategy.yaml"

INTERCONNECT_RTL = ROOT / "rtl/interconnect/hello_axi_lite_interconnect.sv"
CONTRACT_RTL = ROOT / "rtl/interconnect/hello_linux_soc_contract.sv"
DRAM_RTL = ROOT / "rtl/memory/hello_axi_lite_dram.sv"

REQUIRED_UMA_AXES = {
    "coherency_policy": "uma_coherency_report",
    "iommu_isolation": "iommu_fault_injection_report",
    "memory_qos": "memory_qos_report",
    "android_buffer_lifecycle": "android_shared_buffer_report",
}

REQUIRED_UMA_ARTIFACTS = {
    "docs/evidence/memory/uma_coherency_report.json",
    "docs/evidence/memory/iommu_fault_injection_report.json",
    "docs/evidence/memory/memory_qos_report.json",
    "docs/evidence/android/android_shared_buffer_report.json",
}


def read(path: Path) -> str:
    return path.read_text(errors="ignore")


def h(value: str) -> int:
    return int(value.replace("_", "").replace("0x", ""), 16)


def fail_unless(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def region(contract: dict, name: str) -> dict:
    for item in contract["hello_chip"]["regions"]:
        if item["name"] == name:
            return item
    raise KeyError(name)


def check_hello_chip_dram_contract(contract: dict, errors: list[str]) -> None:
    dram = region(contract, "dram")
    fail_unless(
        dram["base"] == "0x80000000", "hello-chip DRAM aperture base must remain 0x80000000", errors
    )
    fail_unless(
        dram["size"] == "0x00001000",
        "hello-chip debug DRAM aperture must remain documented as 4 KiB",
        errors,
    )
    fail_unless(
        "Small debug-visible SRAM-backed DRAM aperture" in dram.get("description", ""),
        "hello-chip DRAM contract must say it is a small SRAM-backed aperture",
        errors,
    )
    fail_unless(
        contract["hello_chip"]["has_cpu"] is False,
        "hello-chip platform contract must not imply a production CPU/UMA path",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    memory_map = read(MEMORY_MAP)
    memory_subsystem = read(MEMORY_SUBSYSTEM)
    interconnect = read(INTERCONNECT)
    joined = "\n".join([memory_map, memory_subsystem, interconnect])

    required_tokens = [
        "SRAM-backed",
        "no cache coherency",
        "no IOMMU",
        "no QoS",
        "real memory controller boundary",
        "fail closed",
        "CPU-wins arbitration",
        "bounded physical-address allowlist",
    ]
    for token in required_tokens:
        fail_unless(
            token in joined,
            f"memory/interconnect docs missing required boundary token: {token}",
            errors,
        )

    fail_unless(
        "`0x8000_0000` | `4 KiB`" in memory_map,
        "docs/arch/memory-map.md must keep the hello-chip debug DRAM aperture at 4 KiB",
        errors,
    )
    fail_unless(
        "`0x8000_0000` | `256 MiB`" in memory_map,
        "docs/arch/memory-map.md must document the Linux scaffold DRAM aperture separately",
        errors,
    )
    fail_unless(
        "Real DRAM, PHY timing, refresh, training, ECC, cache coherency, IOMMU/SMMU, and QoS"
        in memory_subsystem,
        "docs/arch/memory-subsystem.md must explicitly block real memory hierarchy claims",
        errors,
    )
    fail_unless(
        "No release, Android, AI-throughput, display-smoothness, or memory-bandwidth claim"
        in interconnect,
        "docs/arch/interconnect.md must document the release claim boundary",
        errors,
    )


def check_rtl_decode(errors: list[str]) -> None:
    rtl = read(INTERCONNECT_RTL)
    contract_rtl = read(CONTRACT_RTL)
    dram_rtl = read(DRAM_RTL)

    required_patterns = {
        "DRAM base constant": r"DRAM_BASE\s*=\s*32'h8000_0000",
        "DRAM 256 MiB mask": r"DRAM_MASK\s*=\s*32'h0FFF_FFFF",
        "DRAM decode": r"\(addr\s*&\s*~DRAM_MASK\)\s*==\s*DRAM_BASE",
        "INTC base constant": r"INTC_BASE\s*=\s*32'h0C00_0000",
        "INTC decode": r"\(addr\s*&\s*~INTC_MASK\)\s*==\s*INTC_BASE",
        "DMA base constant": r"DMA_BASE\s*=\s*32'h1001_0000",
        "DMA decode": r"\(addr\s*&\s*~DMA_MASK\)\s*==\s*DMA_BASE",
        "DECERR/SLVERR response": r"RESP_SLVERR\s*=\s*2'b10",
        "unmapped read value": r"32'hDEAD_BEEF",
    }
    for name, pattern in required_patterns.items():
        fail_unless(re.search(pattern, rtl) is not None, f"interconnect RTL missing {name}", errors)

    fail_unless(
        "grant_dma_wr = !cpu_wr_req && dma_wr_req" in contract_rtl,
        "contract wrapper must preserve CPU-wins write arbitration over DMA",
        errors,
    )
    fail_unless(
        "grant_dma_rd = !cpu_rd_req && dma_rd_req" in contract_rtl,
        "contract wrapper must preserve CPU-wins read arbitration over DMA",
        errors,
    )
    fail_unless(
        "parameter int unsigned DEPTH_WORDS = 1024" in dram_rtl,
        "DRAM model must remain a small 1024-word SRAM stand-in unless docs and tests are updated",
        errors,
    )
    fail_unless(
        "s_axil_bresp <= 2'b10" in dram_rtl and "s_axil_rresp <= 2'b10" in dram_rtl,
        "DRAM model must return SLVERR for out-of-range or unaligned accesses",
        errors,
    )


def check_uma_strategy(errors: list[str]) -> None:
    data = yaml.safe_load(UMA.read_text())
    fail_unless(isinstance(data, dict), "UMA strategy must be a YAML mapping", errors)
    if not isinstance(data, dict):
        return

    fail_unless(
        data.get("schema") == "openphone.uma_coherency_validation_strategy.v1",
        "UMA strategy schema drifted",
        errors,
    )
    fail_unless(
        data.get("status") == "fail_closed_until_evidence",
        "UMA strategy must fail closed until evidence",
        errors,
    )

    axes = data.get("validation_axes")
    fail_unless(isinstance(axes, list), "UMA strategy must list validation_axes", errors)
    axis_by_id = {axis.get("id"): axis for axis in axes or [] if isinstance(axis, dict)}
    for axis_id, gate in REQUIRED_UMA_AXES.items():
        axis = axis_by_id.get(axis_id)
        fail_unless(axis is not None, f"UMA strategy missing axis {axis_id}", errors)
        if not axis:
            continue
        fail_unless(
            axis.get("release_gate") == gate,
            f"UMA axis {axis_id} must release through {gate}",
            errors,
        )
        fail_unless(
            isinstance(axis.get("minimum_tests"), list) and len(axis["minimum_tests"]) >= 4,
            f"UMA axis {axis_id} must list at least four minimum tests",
            errors,
        )
        fail_unless(
            isinstance(axis.get("evidence_gate"), dict)
            and axis["evidence_gate"].get("blocked") is True,
            f"UMA axis {axis_id} must include a blocked evidence_gate",
            errors,
        )

    artifacts = set(data.get("required_artifacts") or [])
    missing = sorted(REQUIRED_UMA_ARTIFACTS - artifacts)
    fail_unless(
        not missing, "UMA strategy missing required artifacts: " + ", ".join(missing), errors
    )

    for claim_rule in data.get("claim_rules") or []:
        fail_unless(
            "blocked" in claim_rule.lower() or "require" in claim_rule.lower(),
            f"UMA claim rule is not fail-closed: {claim_rule}",
            errors,
        )


def check_no_claim_leak(errors: list[str]) -> None:
    combined = "\n".join(
        read(path) for path in (MEMORY_MAP, MEMORY_SUBSYSTEM, INTERCONNECT, UMA)
    ).lower()
    forbidden_claims = [
        "real dram is implemented",
        "lpddr phy is implemented",
        "cache coherency is implemented",
        "iommu is implemented and enabled",
        "qos is implemented and enabled",
        "production uma is implemented",
    ]
    for claim in forbidden_claims:
        fail_unless(claim not in combined, f"forbidden unsupported claim present: {claim}", errors)


def main() -> int:
    errors: list[str] = []
    contract = json.loads(PLATFORM.read_text())
    check_hello_chip_dram_contract(contract, errors)
    check_docs(errors)
    check_rtl_decode(errors)
    check_uma_strategy(errors)
    check_no_claim_leak(errors)

    if errors:
        print("Memory/interconnect contract check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Memory/interconnect contract check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
