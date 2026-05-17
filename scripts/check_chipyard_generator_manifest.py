#!/usr/bin/env python3
"""Fail-closed checks for the selected Chipyard/Rocket CPU/AP path."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from cpu_ap_evidence_lib import (
    EXPECTED_CHIPYARD,
    GENERATED_MANIFEST,
    IMPORT_TEMPLATE,
    ROOT,
    SELECTED_MANIFEST,
    artifact_specs,
    load_evidence_manifest,
    load_json,
    rel,
    require,
    text_problems,
    transcript_specs,
    validate_path_kind,
    validate_sha256,
)


def check_selected_manifest(errors: list[str]) -> None:
    require(
        SELECTED_MANIFEST.is_file(),
        f"missing selected generator manifest: {rel(SELECTED_MANIFEST)}",
        errors,
    )
    require(
        IMPORT_TEMPLATE.is_file(),
        f"missing import manifest template: {rel(IMPORT_TEMPLATE)}",
        errors,
    )
    evidence_manifest = load_evidence_manifest(errors)
    if errors:
        return

    manifest = load_json(SELECTED_MANIFEST)
    chipyard = manifest.get("chipyard", {})
    selected = manifest.get("selected_path", {})
    policy = manifest.get("claim_policy", {})
    phone_target = manifest.get("phone_2028_target_boundary", {})

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
        chipyard.get("repo") == EXPECTED_CHIPYARD["repo"],
        "selected Chipyard repo drifted",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"], "Chipyard tag must stay pinned", errors
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
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
        selected.get("claim_level") == "initial_linux_bringup_only",
        "single-hart Rocket selection must remain an initial Linux bring-up claim only",
        errors,
    )
    require(
        "not competitive with a 2028 phone application processor"
        in selected.get("not_phone_class_reason", ""),
        "selected manifest must explain why single Rocket is not a 2028 phone-class AP",
        errors,
    )
    require(
        phone_target.get("status") == "blocked_not_selected_for_product_claims",
        "2028 phone-class AP target boundary must remain blocked",
        errors,
    )
    required_phone_evidence = phone_target.get("minimum_claim_evidence", [])
    if not isinstance(required_phone_evidence, list):
        errors.append("2028 phone-class AP minimum_claim_evidence must be a list")
    else:
        for token in (
            "RISC-V application profile and extension matrix with ISA compliance results",
            "cache hierarchy, coherency, cache-maintenance, TLB, and MMU validation",
            "CoreMark, STREAM, lmbench, fio, and selected SPEC-like workload results",
            "CTS/VTS/userspace evidence before Android compatibility claims",
        ):
            require(
                token in required_phone_evidence,
                f"2028 phone-class AP target boundary lacks required evidence token: {token}",
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
    require(
        manifest.get("evidence_manifest") == "docs/evidence/cpu-ap-evidence-manifest.json",
        "selected manifest must point to the CPU/AP evidence manifest",
        errors,
    )
    require(
        manifest.get("capture_helper") == "scripts/capture_cpu_ap_evidence.py",
        "selected manifest must point to the CPU/AP evidence capture helper",
        errors,
    )

    expected_artifacts = [rel(GENERATED_MANIFEST)]
    expected_artifacts.extend(
        str(spec["path"])
        for spec in artifact_specs(evidence_manifest).values()
        if isinstance(spec.get("path"), str)
    )
    for path in expected_artifacts:
        require(
            path in manifest.get("expected_generated_artifacts", []),
            f"selected manifest lacks generated artifact: {path}",
            errors,
        )

    for spec in transcript_specs(evidence_manifest).values():
        path = spec.get("path")
        require(
            path in manifest.get("required_evidence", []),
            f"selected manifest lacks evidence artifact: {path}",
            errors,
        )


def check_generated_import_manifest(errors: list[str]) -> None:
    evidence_manifest = load_evidence_manifest(errors)
    require(
        GENERATED_MANIFEST.is_file(),
        f"missing generated import manifest: {rel(GENERATED_MANIFEST)}",
        errors,
    )
    if errors:
        return

    manifest = load_json(GENERATED_MANIFEST)
    chipyard = manifest.get("chipyard", {})
    generation = manifest.get("generation", {})
    artifacts = manifest.get("artifacts", {})
    evidence = manifest.get("evidence", {})
    artifact_hashes = manifest.get("artifact_sha256", {})
    evidence_hashes = manifest.get("evidence_sha256", {})

    require(
        manifest.get("schema") == "openphone.cpu_ap_import_manifest.v1",
        "unexpected generated manifest schema",
        errors,
    )
    require(
        manifest.get("status") in {"generated", "complete", "linux_complete"},
        "generated manifest status must be generated, complete, or linux_complete",
        errors,
    )
    require(
        chipyard.get("repo") == EXPECTED_CHIPYARD["repo"],
        "generated manifest uses an unapproved Chipyard repo",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"],
        "generated manifest uses an unapproved Chipyard tag",
        errors,
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
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
    require(
        generation.get("bootstrap_preflight_report")
        == "build/chipyard/openphone_rocket/bootstrap-preflight.json",
        "generated manifest must reference the bootstrap preflight report",
        errors,
    )
    preflight_report = generation.get("bootstrap_preflight_report")
    if isinstance(preflight_report, str):
        check_bootstrap_preflight_report(ROOT / preflight_report, errors)
    require(
        generation.get("verilator_preflight_report")
        == "build/chipyard/openphone_rocket/verilator-preflight.json",
        "generated manifest must reference the Verilator preflight report",
        errors,
    )
    verilator_preflight_report = generation.get("verilator_preflight_report")
    if isinstance(verilator_preflight_report, str):
        check_verilator_preflight_report(ROOT / verilator_preflight_report, errors)
    require(
        bool(generation.get("command")), "generated manifest must record generation command", errors
    )
    require(
        bool(generation.get("tool_versions")),
        "generated manifest must record tool versions",
        errors,
    )
    require(
        bool(generation.get("generated_at_utc")),
        "generated manifest must record generated_at_utc",
        errors,
    )
    require(
        isinstance(artifact_hashes, dict),
        "generated manifest artifact_sha256 must be an object",
        errors,
    )
    require(
        isinstance(evidence_hashes, dict),
        "generated manifest evidence_sha256 must be an object",
        errors,
    )
    if not isinstance(artifacts, dict) or not isinstance(evidence, dict):
        errors.append("generated manifest artifacts and evidence fields must be objects")
        return

    require_simulator_executable = manifest.get("status") in {"complete", "linux_complete"}
    for name, spec in artifact_specs(evidence_manifest).items():
        expected_path = spec.get("path")
        path = artifacts.get(name, "")
        require(
            path == expected_path, f"generated manifest {name} path must be {expected_path}", errors
        )
        if not isinstance(path, str) or not path:
            continue
        artifact_path = ROOT / path
        validation_spec = dict(spec)
        if name == "simulator" and not require_simulator_executable:
            validation_spec["requires_executable"] = False
        validate_path_kind(artifact_path, validation_spec, errors, name)
        if artifact_path.exists():
            if artifact_path.is_file():
                required_strings = spec.get("required_strings", [])
                text = artifact_path.read_text(encoding="utf-8", errors="ignore")
                missing = [
                    term for term in required_strings if isinstance(term, str) and term not in text
                ]
                if missing:
                    errors.append(
                        f"{path} missing required generated-artifact markers: " + ", ".join(missing)
                    )
                min_bytes = int(spec.get("min_bytes", 0))
                if min_bytes and artifact_path.stat().st_size < min_bytes:
                    errors.append(f"{path} is smaller than required minimum {min_bytes} bytes")
            validate_sha256(
                artifact_path,
                artifact_hashes,
                name,
                str(spec.get("sha256_key")),
                errors,
            )

    require_linux_evidence = manifest.get("status") == "linux_complete"
    for name, spec in transcript_specs(evidence_manifest).items():
        expected_path = spec.get("path")
        path = evidence.get(name, "")
        require(
            path == expected_path, f"generated manifest {name} path must be {expected_path}", errors
        )
        if not isinstance(path, str) or not path:
            continue
        evidence_path = ROOT / path
        if not require_linux_evidence and not evidence_path.is_file():
            continue
        require(evidence_path.is_file(), f"evidence artifact does not exist: {path}", errors)
        if evidence_path.is_file():
            text = evidence_path.read_text(encoding="utf-8", errors="ignore")
            errors.extend(text_problems(text, spec, path, raw=False))
            validate_sha256(
                evidence_path,
                evidence_hashes,
                name,
                str(spec.get("sha256_key")),
                errors,
            )

    linux_contract = subprocess.run(
        [sys.executable, "scripts/check_chipyard_generated_linux_contract.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(
        linux_contract.returncode == 0,
        "generated Linux DTS/memmap/regmap contract failed:\n" + linux_contract.stdout.rstrip(),
        errors,
    )


def check_bootstrap_preflight_report(path: Path, errors: list[str]) -> None:
    require(path.is_file(), f"missing bootstrap preflight report: {rel(path)}", errors)
    if not path.is_file():
        return

    try:
        report = load_json(path)
    except ValueError as exc:
        errors.append(f"{rel(path)} is invalid JSON: {exc}")
        return

    chipyard = report.get("chipyard", {})
    selected = report.get("selected_path", {})
    require(
        report.get("schema") == "openphone.cpu_ap_bootstrap_preflight.v1",
        "bootstrap preflight report schema drifted",
        errors,
    )
    require(
        report.get("status") == "pass",
        "bootstrap preflight report must pass before generated import claims",
        errors,
    )
    for error in report.get("errors", []):
        if isinstance(error, str) and error:
            errors.append(f"bootstrap preflight error: {error}")
    for blocker in report.get("blockers", []):
        if isinstance(blocker, str) and blocker:
            errors.append(f"bootstrap preflight blocker: {blocker}")
    require(
        chipyard.get("repo") == EXPECTED_CHIPYARD["repo"],
        "bootstrap preflight report uses an unapproved Chipyard repo",
        errors,
    )
    require(
        chipyard.get("tag") == EXPECTED_CHIPYARD["tag"],
        "bootstrap preflight report uses an unapproved Chipyard tag",
        errors,
    )
    require(
        chipyard.get("commit") == EXPECTED_CHIPYARD["commit"],
        "bootstrap preflight report uses an unapproved Chipyard commit",
        errors,
    )
    require(
        selected.get("config_name") == "OpenPhoneRocketConfig",
        "bootstrap preflight report must target OpenPhoneRocketConfig",
        errors,
    )
    require(
        selected.get("core") == "Rocket",
        "bootstrap preflight report must target Rocket",
        errors,
    )
    require(
        selected.get("isa") == "RV64GC", "bootstrap preflight report must target RV64GC", errors
    )
    require(selected.get("harts") == 1, "bootstrap preflight report must target one hart", errors)


def check_verilator_preflight_report(path: Path, errors: list[str]) -> None:
    require(path.is_file(), f"missing Verilator preflight report: {rel(path)}", errors)
    if not path.is_file():
        return

    try:
        report = load_json(path)
    except ValueError as exc:
        errors.append(f"{rel(path)} is invalid JSON: {exc}")
        return

    require(
        report.get("schema") == "openphone.cpu_ap_chipyard_verilator_preflight.v1",
        "Verilator preflight report schema drifted",
        errors,
    )
    require(
        report.get("status") == "pass",
        "Verilator preflight report must pass before generated import claims",
        errors,
    )
    require(
        report.get("config") == "OpenPhoneRocketConfig",
        "Verilator preflight report must target OpenPhoneRocketConfig",
        errors,
    )
    require(
        report.get("config_package") == "openphone",
        "Verilator preflight report must target package openphone",
        errors,
    )
    for error in report.get("errors", []):
        if isinstance(error, str) and error:
            errors.append(f"Verilator preflight error: {error}")
    for blocker in report.get("blockers", []):
        if isinstance(blocker, str) and blocker:
            errors.append(f"Verilator preflight blocker: {blocker}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-generated", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    check_selected_manifest(errors)
    generated_missing = args.require_generated and not GENERATED_MANIFEST.is_file()
    if args.require_generated and not generated_missing:
        check_generated_import_manifest(errors)

    if errors:
        print("Chipyard/Rocket generator check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("STATUS: PASS chipyard.generator_manifest - selected Rocket RV64GC AP path is pinned")
    if generated_missing:
        print(
            "STATUS: BLOCKED chipyard.generated_import - missing "
            f"{rel(GENERATED_MANIFEST)}; pinned checkout/preflight may be ready, but "
            "OpenPhoneRocketConfig has not been generated/imported yet"
        )
        if os.environ.get("REQUIRE_CHIPYARD_GENERATED") == "1":
            return 1
    elif not GENERATED_MANIFEST.is_file():
        print(
            "STATUS: BLOCKED chipyard.generated_import - missing "
            f"{rel(GENERATED_MANIFEST)}; run scripts/bootstrap_chipyard.sh, generate "
            "OpenPhoneRocketConfig, fill the import manifest, then run make "
            "chipyard-generated-check cpu-ap-evidence-check cpu-ap-completion-gate"
        )
    elif args.require_generated:
        print("STATUS: PASS chipyard.generated_import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
