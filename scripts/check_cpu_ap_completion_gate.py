#!/usr/bin/env python3
"""Gate real RV64GC/Linux AP completion claims on generated artifacts and boot evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTED_MANIFEST = ROOT / "generators/chipyard/openphone-rocket-manifest.json"
GENERATED_MANIFEST = ROOT / "build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json"
PLATFORM_CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"

EXPECTED_CHIPYARD = {
    "tag": "1.13.0",
    "commit": "69eba860a352343e4ac6b6df0f3638a79a86ec78",
}

REQUIRED_ARTIFACTS = {
    "verilog": "build/chipyard/openphone_rocket/openphone_rocket_ap.v",
    "dts": "build/chipyard/openphone_rocket/openphone-hello.dts",
    "simulator": "build/chipyard/openphone_rocket/simulator",
}

REQUIRED_EVIDENCE = {
    "opensbi_boot_log": (
        "build/evidence/cpu_ap/openphone_hello_opensbi_boot.log",
        (
            "Reset PC",
            "hart ID",
            "misa",
            "mstatus",
            "mtvec",
            "timer source",
            "interrupt controller",
            "UART console",
            "DRAM base",
            "OpenSBI next-stage handoff",
        ),
    ),
    "linux_boot_log": (
        "build/evidence/cpu_ap/openphone_hello_linux_boot.log",
        (
            "Linux early console",
            "generated DTS hash",
            "memory node",
            "CPU node",
            "timer node",
            "interrupt-controller node",
            "UART node",
            "initramfs start",
            "hello MMIO smoke result",
        ),
    ),
    "trap_timer_irq_log": (
        "build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log",
        (
            "mcause",
            "mepc",
            "mtval",
            "access-fault",
            "mtimecmp",
            "msip",
            "external interrupt claim/complete",
            "mret",
        ),
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def completion_claimed(selected: dict, platform: dict) -> bool:
    claim_policy = selected.get("claim_policy", {})
    return any(
        (
            selected.get("status") in {"generated", "complete", "linux_complete"},
            claim_policy.get("linux_capable_cpu_claim") is True,
            claim_policy.get("platform_contract_has_cpu_may_flip_to_true") is True,
            platform.get("hello_chip", {}).get("has_cpu") is True,
        )
    )


def check_selected_manifest(selected: dict, errors: list[str]) -> None:
    chipyard = selected.get("chipyard", {})
    path = selected.get("selected_path", {})
    policy = selected.get("claim_policy", {})

    require(
        selected.get("schema") == "openphone.cpu_ap_generator_manifest.v1",
        "selected manifest schema drifted",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"], "selected Chipyard tag drifted", errors
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
        "selected Chipyard commit drifted",
        errors,
    )
    require(path.get("generator") == "Chipyard", "selected generator must be Chipyard", errors)
    require(path.get("core") == "Rocket", "selected CPU core must be Rocket", errors)
    require(path.get("isa") == "RV64GC", "selected CPU ISA must be RV64GC", errors)
    require(
        path.get("config_name") == "OpenPhoneRocketConfig",
        "selected config must be OpenPhoneRocketConfig",
        errors,
    )

    if selected.get("status") == "selected_not_generated":
        require(
            policy.get("linux_capable_cpu_claim") is False,
            "non-generated manifest cannot claim Linux-capable CPU",
            errors,
        )
        require(
            policy.get("platform_contract_has_cpu_may_flip_to_true") is False,
            "non-generated manifest cannot allow has_cpu=true",
            errors,
        )


def check_generated_manifest(errors: list[str]) -> dict:
    require(
        GENERATED_MANIFEST.is_file(),
        f"missing generated import manifest: {GENERATED_MANIFEST.relative_to(ROOT)}",
        errors,
    )
    if errors:
        return {}

    generated = load_json(GENERATED_MANIFEST)
    chipyard = generated.get("chipyard", {})
    generation = generated.get("generation", {})

    require(
        generated.get("schema") == "openphone.cpu_ap_import_manifest.v1",
        "generated manifest schema drifted",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"],
        "generated manifest Chipyard tag drifted",
        errors,
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
        "generated manifest Chipyard commit drifted",
        errors,
    )
    require(
        chipyard.get("recursive_submodules_recorded") is True,
        "generated manifest must record recursive submodules",
        errors,
    )
    require(
        bool(chipyard.get("submodules")), "generated manifest must include submodule SHAs", errors
    )
    require(
        generation.get("config") == "OpenPhoneRocketConfig",
        "generated manifest must name OpenPhoneRocketConfig",
        errors,
    )
    return generated


def check_artifacts(generated: dict, errors: list[str]) -> None:
    artifacts = generated.get("artifacts", {})
    for name, expected_path in REQUIRED_ARTIFACTS.items():
        manifest_path = artifacts.get(name)
        require(
            manifest_path == expected_path,
            f"generated manifest {name} path must be {expected_path}",
            errors,
        )
        require(
            (ROOT / expected_path).exists(),
            f"missing generated {name} artifact: {expected_path}",
            errors,
        )


def check_evidence(generated: dict, errors: list[str]) -> None:
    evidence = generated.get("evidence", {})
    for name, (expected_path, markers) in REQUIRED_EVIDENCE.items():
        manifest_path = evidence.get(name)
        require(
            manifest_path == expected_path,
            f"generated manifest {name} path must be {expected_path}",
            errors,
        )
        path = ROOT / expected_path
        require(path.is_file(), f"missing CPU/AP evidence log: {expected_path}", errors)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            require(marker in text, f"{expected_path} lacks required marker: {marker}", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    selected = load_json(SELECTED_MANIFEST)
    platform = load_json(PLATFORM_CONTRACT)
    check_selected_manifest(selected, errors)

    claimed = completion_claimed(selected, platform)
    if claimed or args.require_complete:
        generated = check_generated_manifest(errors)
        if generated:
            check_artifacts(generated, errors)
            check_evidence(generated, errors)

    if errors:
        print(
            "STATUS: FAIL cpu_ap.completion_gate - real RV64GC/Linux AP claim is not backed by required artifacts"
        )
        for error in errors:
            print(f"  - {error}")
        return 1

    if claimed:
        print(
            "STATUS: PASS cpu_ap.completion_gate - generated Rocket RV64GC AP artifacts and boot evidence are present"
        )
        return 0

    print(
        "STATUS: BLOCKED cpu_ap.completion_gate - no real RV64GC/Linux AP completion claim; generated artifacts and boot evidence are absent"
    )
    return 2 if args.require_complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
