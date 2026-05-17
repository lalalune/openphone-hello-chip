#!/usr/bin/env python3
"""Fail-closed checks for the selected Chipyard/Rocket CPU/AP path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "generators/chipyard/openphone-rocket-manifest.json"
TEMPLATE = ROOT / "generators/chipyard/import-manifest.template.json"
BUILD_MANIFEST = ROOT / "build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_selected_manifest(errors: list[str]) -> None:
    require(SELECTED.is_file(), f"missing selected generator manifest: {SELECTED}", errors)
    require(TEMPLATE.is_file(), f"missing import manifest template: {TEMPLATE}", errors)
    if errors:
        return

    manifest = load_json(SELECTED)
    chipyard = manifest.get("chipyard", {})
    selected = manifest.get("selected_path", {})
    policy = manifest.get("claim_policy", {})

    require(
        manifest.get("schema") == "openphone.cpu_ap_generator_manifest.v1",
        "unexpected selected manifest schema",
        errors,
    )
    require(
        manifest.get("status") == "selected_not_generated",
        "selected manifest must remain selected_not_generated until artifacts exist",
        errors,
    )
    require(
        chipyard.get("repo") == "https://github.com/ucb-bar/chipyard.git",
        "selected Chipyard repo drifted",
        errors,
    )
    require(chipyard.get("tag") == "1.13.0", "Chipyard tag must stay pinned", errors)
    require(
        chipyard.get("commit") == "69eba860a352343e4ac6b6df0f3638a79a86ec78",
        "Chipyard commit must stay pinned",
        errors,
    )
    require(selected.get("generator") == "Chipyard", "selected generator must be Chipyard", errors)
    require(selected.get("core") == "Rocket", "selected CPU core must be Rocket", errors)
    require(selected.get("isa") == "RV64GC", "selected CPU ISA must be RV64GC", errors)
    require(
        selected.get("harts") == 1,
        "initial AP integration must be single-hart until boot evidence exists",
        errors,
    )
    require(
        selected.get("config_name") == "OpenPhoneRocketConfig",
        "config name must be OpenPhoneRocketConfig",
        errors,
    )
    require(
        policy.get("linux_capable_cpu_claim") is False,
        "Linux CPU claim must be false without boot evidence",
        errors,
    )
    require(
        policy.get("platform_contract_has_cpu_may_flip_to_true") is False,
        "platform has_cpu flip must remain blocked without generated artifacts",
        errors,
    )

    for path in (
        "build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json",
        "build/chipyard/openphone_rocket/openphone-hello.dts",
        "build/chipyard/openphone_rocket/openphone_rocket_ap.v",
        "build/chipyard/openphone_rocket/simulator",
    ):
        require(
            path in manifest.get("expected_generated_artifacts", []),
            f"selected manifest lacks generated artifact: {path}",
            errors,
        )

    for path in (
        "build/evidence/cpu_ap/openphone_hello_opensbi_boot.log",
        "build/evidence/cpu_ap/openphone_hello_linux_boot.log",
        "build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log",
    ):
        require(
            path in manifest.get("required_evidence", []),
            f"selected manifest lacks evidence artifact: {path}",
            errors,
        )


def check_generated_import_manifest(errors: list[str]) -> None:
    require(
        BUILD_MANIFEST.is_file(), f"missing generated import manifest: {BUILD_MANIFEST}", errors
    )
    if errors:
        return

    manifest = load_json(BUILD_MANIFEST)
    chipyard = manifest.get("chipyard", {})
    generation = manifest.get("generation", {})
    artifacts = manifest.get("artifacts", {})
    evidence = manifest.get("evidence", {})

    require(
        manifest.get("schema") == "openphone.cpu_ap_import_manifest.v1",
        "unexpected generated manifest schema",
        errors,
    )
    require(
        chipyard.get("tag") == "1.13.0",
        "generated manifest uses an unapproved Chipyard tag",
        errors,
    )
    require(
        chipyard.get("commit") == "69eba860a352343e4ac6b6df0f3638a79a86ec78",
        "generated manifest uses an unapproved Chipyard commit",
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
        "generated manifest must use OpenPhoneRocketConfig",
        errors,
    )

    for name in ("verilog", "dts", "simulator"):
        path = artifacts.get(name, "")
        require(bool(path), f"generated manifest lacks artifact path: {name}", errors)
        require(
            bool(path) and (ROOT / path).exists(),
            f"generated artifact does not exist: {path}",
            errors,
        )

    for name in ("opensbi_boot_log", "linux_boot_log", "trap_timer_irq_log"):
        path = evidence.get(name, "")
        require(bool(path), f"generated manifest lacks evidence path: {name}", errors)
        require(
            bool(path) and (ROOT / path).is_file(),
            f"evidence artifact does not exist: {path}",
            errors,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-generated", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    check_selected_manifest(errors)
    if args.require_generated:
        check_generated_import_manifest(errors)

    if errors:
        print("Chipyard/Rocket generator check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("STATUS: PASS chipyard.generator_manifest - selected Rocket RV64GC AP path is pinned")
    if not BUILD_MANIFEST.is_file():
        print(
            f"STATUS: BLOCKED chipyard.generated_import - missing {BUILD_MANIFEST.relative_to(ROOT)}"
        )
    elif args.require_generated:
        print("STATUS: PASS chipyard.generated_import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
