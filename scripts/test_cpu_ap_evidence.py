#!/usr/bin/env python3
"""Unit tests for CPU/AP claim-boundary and evidence-gate semantics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import capture_cpu_ap_evidence  # noqa: E402
from cpu_ap_evidence_lib import (  # noqa: E402
    EVIDENCE_MANIFEST,
    SELECTED_MANIFEST,
    load_json,
    text_problems,
    transcript_specs,
    validate_evidence_manifest,
)


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"missing {expected!r} in output:\n{text}")


def test_evidence_manifest_blocks_phone_class_claims() -> None:
    manifest = load_json(EVIDENCE_MANIFEST)
    errors: list[str] = []
    validate_evidence_manifest(manifest, errors)
    if errors:
        raise AssertionError("\n".join(errors))

    policy = manifest["target_policy"]
    if policy["initial_linux_bringup_claim"] != "single_hart_rocket_rv64gc_linux_smoke_only":
        raise AssertionError("initial Rocket target claim boundary drifted")
    if policy["phone_2028_ap_claim"] != "blocked_until_phone_class_artifacts_and_evidence_pass":
        raise AssertionError("2028 phone-class AP claim is no longer blocked")
    required = set(policy["phone_2028_claim_requires"])
    for item in (
        "riscv_application_profile_and_extension_matrix",
        "cache_hierarchy_and_coherency_evidence",
        "mmu_page_table_and_tlb_evidence",
        "sustained_boot_and_benchmark_evidence",
        "power_thermal_voltage_frequency_evidence",
        "android_cts_vts_and_userspace_evidence",
    ):
        if item not in required:
            raise AssertionError(f"missing 2028 phone-class requirement: {item}")


def test_selected_manifest_keeps_single_rocket_as_bringup_only() -> None:
    manifest = json.loads(SELECTED_MANIFEST.read_text())
    selected = manifest["selected_path"]
    if selected["claim_level"] != "initial_linux_bringup_only":
        raise AssertionError("single Rocket target must remain bring-up only")
    assert_contains(
        selected["not_phone_class_reason"],
        "not competitive with a 2028 phone application processor",
    )

    phone_target = manifest["phone_2028_target_boundary"]
    if phone_target["status"] != "blocked_not_selected_for_product_claims":
        raise AssertionError("phone-class target boundary must remain blocked")
    joined = "\n".join(phone_target["minimum_claim_evidence"])
    for token in ("ISA compliance", "cache hierarchy", "MMU", "CoreMark", "CTS/VTS"):
        assert_contains(joined, token)


def test_capture_helper_knows_new_cpu_ap_transcripts() -> None:
    modes = capture_cpu_ap_evidence.MODE_TO_TRANSCRIPT
    if modes["isa-cache-mmu"] != ("isa_cache_mmu_log", "openphone_hello_isa_cache_mmu"):
        raise AssertionError("isa-cache-mmu capture mode drifted")
    if modes["ap-benchmarks"] != ("ap_benchmark_log", "openphone_hello_ap_benchmarks"):
        raise AssertionError("ap-benchmarks capture mode drifted")
    if capture_cpu_ap_evidence.MODE_ENV["linux-boot"] != "OPENPHONE_LINUX_BOOT_CMD":
        raise AssertionError("Linux boot command env drifted")


def test_capture_template_lists_required_markers_and_no_pass_claim() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/capture_cpu_ap_evidence.py", "template", "linux-boot"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    assert_contains(
        result.stdout, "destination: build/evidence/cpu_ap/openphone_hello_linux_boot.log"
    )
    assert_contains(result.stdout, "command env: OPENPHONE_LINUX_BOOT_CMD")
    assert_contains(result.stdout, "Linux early console")
    assert_contains(
        result.stdout, "openphone-evidence: replace_this_file_with_real_generated_ap_output=true"
    )
    if "openphone-evidence: status=PASS" in result.stdout:
        raise AssertionError("template must not claim PASS evidence")


def test_new_transcripts_reject_placeholder_or_incomplete_text() -> None:
    manifest = load_json(EVIDENCE_MANIFEST)
    specs = transcript_specs(manifest)
    for key in ("isa_cache_mmu_log", "ap_benchmark_log"):
        with_placeholder = "placeholder\nopenphone-evidence: status=PASS\n"
        problems = text_problems(with_placeholder, specs[key], key, raw=True)
        joined = "\n".join(problems)
        assert_contains(joined, "contains forbidden placeholder/failure markers")
        assert_contains(joined, "missing required transcript markers")


def test_scaffold_check_lists_new_missing_evidence_paths() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_cpu_ap_evidence.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    assert_contains(result.stdout, "STATUS: PASS cpu_ap.scaffold")
    assert_contains(result.stdout, "openphone_hello_isa_cache_mmu.log")
    assert_contains(result.stdout, "openphone_hello_ap_benchmarks.log")


def main() -> int:
    tests = [
        test_evidence_manifest_blocks_phone_class_claims,
        test_selected_manifest_keeps_single_rocket_as_bringup_only,
        test_capture_helper_knows_new_cpu_ap_transcripts,
        test_capture_template_lists_required_markers_and_no_pass_claim,
        test_new_transcripts_reject_placeholder_or_incomplete_text,
        test_scaffold_check_lists_new_missing_evidence_paths,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
