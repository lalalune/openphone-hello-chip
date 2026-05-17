#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/evidence/memory/uma-dram-evidence-gate.yaml"
MEMORY = ROOT / "docs/arch/memory-subsystem.md"
INTERCONNECT = ROOT / "docs/arch/interconnect.md"
MEMORY_MAP = ROOT / "docs/arch/memory-map.md"
DRAM_RTL = ROOT / "rtl/memory/hello_axi_lite_dram.sv"
CONTRACT_RTL = ROOT / "rtl/interconnect/hello_linux_soc_contract.sv"
CONTRACT_TEST = ROOT / "verify/cocotb/test_cpu_mem_intc_contract.py"

REQUIRED_BLOCKED = {
    "real_dram_controller_phy",
    "uma_cache_coherency",
    "iommu_smmu_dma_isolation",
    "memory_qos_bandwidth",
}

REQUIRED_EVIDENCE_BY_CLAIM = {
    "real_dram_controller_phy": {
        "docs/evidence/memory/real_dram_controller_phy_report.json",
        "docs/evidence/memory/dram_training_timing_report.json",
    },
    "uma_cache_coherency": {
        "docs/evidence/memory/uma_coherency_report.json",
        "docs/evidence/memory/shared_buffer_negative_sync_report.json",
    },
    "iommu_smmu_dma_isolation": {
        "docs/evidence/memory/iommu_fault_injection_report.json",
        "docs/evidence/memory/dma_isolation_fault_visibility_report.json",
    },
    "memory_qos_bandwidth": {
        "docs/evidence/memory/memory_qos_report.json",
        "docs/evidence/memory/contended_bandwidth_latency_report.json",
    },
}

REQUIRED_DOC_TOKENS = {
    MEMORY: [
        "SRAM-backed",
        "external DRAM controller and PHY",
        "real integration",
        "does not implement a DRAM controller",
        "UMA coherency protocol",
        "IOMMU/SMMU translation",
        "memory QoS",
        "must not be used as release evidence",
    ],
    INTERCONNECT: [
        "not an IOMMU",
        "SRAM-backed DRAM model",
        "remain blocked",
    ],
    MEMORY_MAP: [
        "SRAM-backed",
        "not an IOMMU or coherency implementation",
    ],
}

FORBIDDEN_POSITIVE_CLAIMS = [
    r"\breal\s+DRAM\s+(?:controller|PHY)\s+(?:is\s+)?(?:implemented|validated|proven)\b",
    r"\bUMA\s+coherency\s+(?:is\s+)?(?:implemented|validated|proven)\b",
    r"\b(?:IOMMU|SMMU)\s+(?:is\s+)?(?:implemented|validated|proven|enabled)\b",
    r"\bmemory\s+QoS\s+(?:is\s+)?(?:implemented|validated|proven|enabled)\b",
    r"\bcoherent\s+DMA\s+(?:is\s+)?(?:implemented|validated|proven|enabled)\b",
]


def read(path: Path) -> str:
    return path.read_text(errors="ignore")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def valid_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def check_gate(errors: list[str]) -> None:
    if not GATE.is_file():
        errors.append(f"missing {GATE.relative_to(ROOT)}")
        return

    data = yaml.safe_load(GATE.read_text())
    if not isinstance(data, dict):
        errors.append(f"{GATE.relative_to(ROOT)} must be a YAML mapping")
        return

    require(
        data.get("schema") == "openphone.memory_uma_evidence_gate.v1",
        "memory/UMA gate schema drifted",
        errors,
    )
    require(
        data.get("status") == "scaffold_only_real_claims_blocked",
        "memory/UMA gate must stay scaffold_only_real_claims_blocked",
        errors,
    )

    scaffold = data.get("current_scaffold_evidence")
    require(isinstance(scaffold, dict), "memory/UMA gate missing current_scaffold_evidence", errors)
    if isinstance(scaffold, dict):
        require(
            scaffold.get("claim_level") == "local_scaffold_only",
            "scaffold claim level must be local_scaffold_only",
            errors,
        )
        checks = scaffold.get("executable_checks")
        require(
            isinstance(checks, list) and bool(checks),
            "scaffold evidence must list executable checks",
            errors,
        )
        commands = {item.get("command") for item in checks or [] if isinstance(item, dict)}
        require(
            "make memory-uma-claim-gate" in commands,
            "gate must list make memory-uma-claim-gate",
            errors,
        )
        require(
            "make cocotb-contract" in commands,
            "gate must list cocotb contract simulation as executable evidence",
            errors,
        )

    non_goals = "\n".join(data.get("non_goals") or [])
    for token in (
        "Real DRAM controller",
        "UMA cache coherency",
        "IOMMU/SMMU translation",
        "Memory QoS",
    ):
        require(token in non_goals, f"memory/UMA gate non_goals missing token: {token}", errors)

    blocked = data.get("blocked_real_claims")
    require(isinstance(blocked, list), "memory/UMA gate must list blocked_real_claims", errors)
    blocked_by_id = {item.get("id"): item for item in blocked or [] if isinstance(item, dict)}
    missing = sorted(REQUIRED_BLOCKED - set(blocked_by_id))
    require(not missing, "memory/UMA gate missing blocked claim ids: " + ", ".join(missing), errors)
    for claim_id in sorted(REQUIRED_BLOCKED & set(blocked_by_id)):
        claim = blocked_by_id[claim_id]
        require(claim.get("status") == "blocked", f"{claim_id} must remain blocked", errors)
        require(
            isinstance(claim.get("reason"), str) and claim["reason"],
            f"{claim_id} missing reason",
            errors,
        )
        unblock = claim.get("unblock_requires")
        require(
            isinstance(unblock, list)
            and len(unblock) >= 2
            and all(isinstance(item, str) and item for item in unblock),
            f"{claim_id} must list unblock requirements",
            errors,
        )
        artifacts = claim.get("evidence_artifacts")
        require(
            isinstance(artifacts, list) and len(artifacts) >= 2,
            f"{claim_id} must list evidence_artifacts",
            errors,
        )
        artifact_set = set(artifacts or [])
        missing_artifacts = sorted(REQUIRED_EVIDENCE_BY_CLAIM[claim_id] - artifact_set)
        require(
            not missing_artifacts,
            f"{claim_id} missing required evidence_artifacts: " + ", ".join(missing_artifacts),
            errors,
        )
        for artifact in artifacts or []:
            require(
                valid_relative_path(artifact),
                f"{claim_id} evidence artifact must be a relative repo path: {artifact}",
                errors,
            )
            if valid_relative_path(artifact):
                require(
                    not (ROOT / artifact).exists(),
                    f"{claim_id} is still blocked but evidence artifact exists: {artifact}",
                    errors,
                )

    rules = "\n".join(data.get("claim_rules") or [])
    for token in ("must not", "real DRAM", "UMA coherency", "IOMMU/SMMU", "QoS", "executable RTL"):
        require(token in rules, f"claim rules missing boundary token: {token}", errors)


def check_docs(errors: list[str]) -> None:
    for path, tokens in REQUIRED_DOC_TOKENS.items():
        text = read(path)
        for token in tokens:
            require(token in text, f"{path.relative_to(ROOT)} missing token: {token}", errors)

    combined = "\n".join(read(path) for path in (MEMORY, INTERCONNECT, MEMORY_MAP, GATE))
    for pattern in FORBIDDEN_POSITIVE_CLAIMS:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        require(
            match is None,
            f"unsupported positive memory/UMA claim present: {match.group(0) if match else pattern}",
            errors,
        )


def check_rtl_and_tests(errors: list[str]) -> None:
    dram = read(DRAM_RTL)
    contract = read(CONTRACT_RTL)
    test = read(CONTRACT_TEST)

    require("module hello_axi_lite_dram" in dram, "DRAM scaffold module missing", errors)
    require(
        "logic [31:0] mem [0:DEPTH_WORDS-1]" in dram, "DRAM model must remain SRAM-backed", errors
    )
    require(
        "parameter int unsigned DEPTH_WORDS = 1024" in dram,
        "DRAM model depth changed without gate update",
        errors,
    )
    require("s_axil_bresp <= 2'b10" in dram, "DRAM write error path must return SLVERR", errors)
    require("s_axil_rresp <= 2'b10" in dram, "DRAM read error path must return SLVERR", errors)

    require(
        "grant_dma_wr = !cpu_wr_req && dma_wr_req" in contract,
        "DMA write arbitration contract changed",
        errors,
    )
    require(
        "grant_dma_rd = !cpu_rd_req && dma_rd_req" in contract,
        "DMA read arbitration contract changed",
        errors,
    )
    require(
        "dma_mem_awaddr - 32'h8000_0000" in contract,
        "DMA write path must remain translated into DRAM-local space",
        errors,
    )
    require(
        "dma_mem_araddr - 32'h8000_0000" in contract,
        "DMA read path must remain translated into DRAM-local space",
        errors,
    )

    require(
        "dma_non_dram_targets_fault_without_mmio_side_effects" in test,
        "cocotb contract must include DMA non-DRAM containment test",
        errors,
    )
    require(
        "0x0C00_0008" in test and "0x1001_0038" in test,
        "DMA containment test must check MMIO side effects and error count",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    check_gate(errors)
    check_docs(errors)
    check_rtl_and_tests(errors)

    if errors:
        print("Memory/UMA claim gate failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Memory/UMA claim gate passed: scaffold evidence is separated from real DRAM/UMA/IOMMU claims."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
