#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

REQUIRED = [
    "build/netlist/hello_chip_synth.v",
    "build/reports/hello_soc_yosys.log",
    "build/reports/tool_versions.txt",
    "build/reports/cocotb/manifest.json",
    "build/reports/formal_manifest.json",
    "build/verilator/Vhello_chip_top",
]

COCOTB_TARGETS = {
    "hello_chip_top_test_hello_chip",
    "hello_display_test_hello_display",
    "hello_dma_test_hello_dma",
    "hello_linux_soc_contract_test_cpu_mem_intc_contract",
    "hello_npu_test_hello_npu",
    "hello_tiny_cpu_contract_tb_test_cpu_mem_intc_contract",
    "hello_tiny_cpu_contract_tb_test_tiny_cpu_execution",
}

FORMAL_TARGETS = {
    "hello_dbg_mmio_bridge",
    "hello_npu",
    "hello_dma",
    "hello_soc_top",
}

REQUIRED_SOURCE = [
    "scripts/check_software_bsp.py",
    "scripts/check_mvp_status.py",
    "scripts/check_prototype_status_dashboard.py",
    "scripts/check_real_world_gates.py",
    "scripts/check_memory_interconnect_contract.py",
    "scripts/check_product_feature_gates.py",
    "scripts/check_physical_closure_work_order.py",
    "docs/toolchain/headless-cli-audit.md",
    "docs/toolchain/README.md",
    "docs/toolchain/benchmark-simulator-critical-gap-audit.md",
    "docs/spec-db/mobile-sota-2026.yaml",
    "docs/benchmarks/benchmark-matrix.md",
    "docs/benchmarks/harness.md",
    "docs/benchmarks/report-schema.yaml",
    "docs/android/riscv-bringup.md",
    "docs/android/bsp-critical-gap-audit-2026-05-17.md",
    "docs/project/three-week-execution-plan.md",
    "docs/project/workstreams.md",
    "docs/project/prototype-status-dashboard.md",
    "docs/project/critical-gap-review-2026-05-17.md",
    "docs/project/rtl-soc-critical-gap-audit.md",
    "docs/project/board-package-pd-fpga-critical-gap-audit.md",
    "docs/risks/risk-register.md",
    "docs/manufacturing/real-world-verification-gaps.yaml",
    "docs/manufacturing/physical-closure-work-order.yaml",
    "docs/manufacturing/product-feature-evidence-manifest.yaml",
    "benchmarks/configs/fio-rand-rw.fio",
    "benchmarks/configs/fio-seq-read.fio",
    "benchmarks/configs/benchmark_plan.json",
    "benchmarks/generate_simulator_arch_metrics.py",
    "benchmarks/install_host_benchmark_tools.py",
    "benchmarks/metadata/local-host-smoke.json",
    "benchmarks/models/mobile_smoke.tflite",
    "benchmarks/tools/coremark",
    "benchmarks/tools/stream_c.exe",
    "benchmarks/tools/bw_mem",
    "benchmarks/tools/lat_mem_rd",
    "benchmarks/tools/benchmark_model",
    "docs/benchmarks/models/README.md",
    "benchmarks/run_benchmarks.py",
    "scripts/test_benchmark_calibration.py",
    "scripts/test_benchmark_parsers.py",
    "scripts/test_simulator_arch_metrics.py",
    "sw/platform/hello_platform_contract.json",
    "sw/platform/generated/hello_platform_contract.h",
    "sw/bootrom/hello_qemu_firmware.S",
    "sw/bootrom/linker.ld",
    "docs/sw/buildroot/README.md",
    "sw/buildroot/external.desc",
    "sw/buildroot/Config.in",
    "sw/buildroot/external.mk",
    "sw/buildroot/scripts/import-buildroot-external.sh",
    "sw/buildroot/configs/openphone_hello_defconfig",
    "sw/buildroot/board/openphone/hello/linux.fragment",
    "sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke",
    "docs/sw/linux/README.md",
    "sw/linux/scripts/import-linux-bsp.sh",
    "sw/linux/dts/openphone-hello.dts",
    "sw/linux/drivers/hello/hello_platform_contract.h",
    "sw/linux/drivers/hello/Kconfig",
    "sw/linux/drivers/hello/Makefile",
    "sw/linux/drivers/hello/hello-npu.c",
    "sw/linux/drivers/hello/hello-dma.c",
    "sw/linux/tests/hello-mmio-smoke.c",
    "docs/sw/aosp-device/README.md",
    "sw/aosp-device/import-aosp-device.sh",
    "sw/aosp-device/manifests/openphone-ai-soc-local.xml",
    "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
    "sw/aosp-device/device/openphone/openphone_ai_soc/fstab.openphone",
    "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
    "sw/aosp-device/device/openphone/openphone_ai_soc/kernel/openphone_ai_soc.fragment",
    "sw/aosp-device/device/openphone/openphone_ai_soc/dts/openphone-hello-android.dts",
    "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
    "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/hello_npu.te",
    "docs/sw/opensbi/README.md",
    "docs/sw/u-boot/README.md",
    "sw/check_bsp_scaffolds.py",
    "verify/check_stub_audit.py",
]


def run_check(root: Path, command: list[str]) -> bool:
    result = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Command failed: {' '.join(command)}")
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
        return False
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_cocotb_manifest(root: Path) -> list[str]:
    data = json.loads((root / "build/reports/cocotb/manifest.json").read_text())
    errors: list[str] = []
    if data.get("schema") != "hello-chip-cocotb-evidence-v1":
        errors.append("cocotb manifest has unexpected schema")
    targets = data.get("targets")
    if not isinstance(targets, dict):
        return errors + ["cocotb manifest missing targets"]
    missing = sorted(COCOTB_TARGETS - set(targets))
    if missing:
        errors.append("cocotb manifest missing target(s): " + ", ".join(missing))
    extra = sorted(set(targets) - COCOTB_TARGETS)
    if extra:
        errors.append("cocotb manifest has stale/unexpected target(s): " + ", ".join(extra))
    for name, entry in targets.items():
        xml = root / entry.get("result_xml", "")
        if not xml.is_file():
            errors.append(f"cocotb {name}: missing result XML")
            continue
        if entry.get("result_sha256") != sha256(xml):
            errors.append(f"cocotb {name}: result XML hash mismatch")
        stats = entry.get("stats", {})
        if stats.get("failures") or stats.get("errors") or not stats.get("testcases"):
            errors.append(f"cocotb {name}: non-passing stats in manifest")
        coverage = entry.get("coverage", {})
        if coverage.get("release_claim") != "blocked_without_functional_coverage":
            errors.append(f"cocotb {name}: coverage summary must block release coverage claims")
        source_hashes = entry.get("source_hashes", {})
        if not isinstance(source_hashes, dict) or not source_hashes:
            errors.append(f"cocotb {name}: missing source hashes")
    return errors


def validate_formal_manifest(root: Path, strict: bool) -> list[str]:
    data = json.loads((root / "build/reports/formal_manifest.json").read_text())
    errors: list[str] = []
    if data.get("schema") != "hello-chip-formal-evidence-v1":
        errors.append("formal manifest has unexpected schema")
    entries = data.get("entries")
    if not isinstance(entries, dict):
        return errors + ["formal manifest missing entries"]
    missing = sorted(FORMAL_TARGETS - set(entries))
    if missing:
        errors.append("formal manifest missing target(s): " + ", ".join(missing))
    for name, entry in entries.items():
        evidence_class = str(entry.get("evidence_class", ""))
        status = entry.get("status")
        paths = entry.get("paths", {})
        if status not in {"pass", "fallback_pass"}:
            errors.append(f"formal {name}: non-passing status {status}")
        if strict and not evidence_class.startswith("sby_"):
            errors.append(f"formal {name}: strict gate rejects {evidence_class}")
        for key in ("status", "log"):
            rel = paths.get(key)
            hash_value = paths.get(f"{key}_sha256")
            if rel:
                artifact = root / rel
                if not artifact.is_file():
                    errors.append(f"formal {name}: missing {key} artifact")
                elif hash_value != sha256(artifact):
                    errors.append(f"formal {name}: {key} hash mismatch")
    if strict and data.get("mode") != "sby-deep-top":
        errors.append("strict pipeline requires formal manifest mode=sby-deep-top")
    if not strict and data.get("release_claim") not in {
        "strict_requires_sby_and_deep_top",
        "strict_formal_bmc_evidence",
    }:
        errors.append("scaffold formal manifest must label strict release boundary")
    source_hashes = data.get("source_hashes", {})
    if not isinstance(source_hashes, dict) or not source_hashes:
        errors.append("formal manifest missing source hashes")
    return errors


def check_headless_audit(root: Path) -> list[str]:
    text = (root / "docs/toolchain/headless-cli-audit.md").read_text(errors="ignore")
    required_terms = [
        "make smoke",
        "make benchmarks-dry-run",
        "make software-bsp-check",
        "make qemu-check",
        "make renode-check",
        "make pipeline-check",
        "make archive-release",
        "No milestone may be marked complete because a GUI action was possible",
    ]
    return [
        f"headless CLI audit missing required evidence path: {term}"
        for term in required_terms
        if term not in text
    ]


def check_benchmark_report(root: Path) -> list[str]:
    report_path = root / "benchmarks/results/pipeline-check/report.json"
    config_path = root / "benchmarks/configs/benchmark_plan.json"
    report = json.loads(report_path.read_text())
    config = json.loads(config_path.read_text())
    errors: list[str] = []

    expected_names = {bench["name"] for bench in config["benchmarks"]}
    result_by_name = {result.get("name"): result for result in report.get("results", [])}
    missing = sorted(expected_names - set(result_by_name))
    if missing:
        errors.append("benchmark dry-run report missing result(s): " + ", ".join(missing))

    for name, result in result_by_name.items():
        status = result.get("status")
        if status == "passed":
            errors.append(f"benchmark dry-run result unexpectedly passed: {name}")
        if status == "blocked" and not result.get("blocked_assets"):
            errors.append(f"benchmark dry-run result blocked without blocked_assets: {name}")
        if status == "planned_missing_deps" and not result.get("missing_dependencies"):
            errors.append(f"benchmark dry-run result missing dependency list: {name}")

    for name in ("tflite_cpu", "tflite_hello_npu"):
        result = result_by_name.get(name)
        if not result:
            continue
        expected_sha = None
        for bench in config["benchmarks"]:
            if bench.get("name") == name:
                artifacts = bench.get("model_artifacts", [])
                expected_sha = artifacts[0].get("sha256") if artifacts else None
        if expected_sha and (root / "benchmarks/models/mobile_smoke.tflite").is_file():
            if result.get("status") == "blocked":
                errors.append(
                    f"{name} is still blocked despite pinned mobile_smoke.tflite artifact"
                )
        elif result.get("status") != "blocked":
            errors.append(
                f"{name} must stay blocked until a real pinned mobile_smoke.tflite artifact exists"
            )

    return errors


def check_mvp_status_semantics(root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "scripts/check_mvp_status.py", "--json"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return ["mvp-status JSON command failed"]

    statuses = json.loads(result.stdout)
    by_name = {item.get("subsystem"): item for item in statuses}
    errors: list[str] = []

    for name in ("qemu", "renode", "benchmarks"):
        item = by_name.get(name)
        if not item:
            errors.append(f"mvp-status missing subsystem: {name}")
            continue
        if item.get("status") == "pass" and item.get("evidence_class") in {
            "scaffold_only",
            "source_present",
            "tool_available",
        }:
            errors.append(
                f"mvp-status lets scaffold/tool/source evidence pass as implementation proof: {name}"
            )

    for item in statuses:
        evidence = item.get("evidence", "").lower()
        if item.get("status") == "pass" and "release check failed" in evidence:
            errors.append(
                f"mvp-status pass row contains release failure text: {item.get('subsystem')}"
            )

    expected_blockers = {
        "qemu": ("qemu_smoke.log", "regen_required", "tool_blocker"),
        "renode": ("renode_smoke.log", "regen_required", "tool_blocker"),
        "benchmarks": ("dry-run planning evidence only", "scaffold_only", "tool_blocker"),
    }
    for name, expected in expected_blockers.items():
        item = by_name.get(name, {})
        if item.get("status") == "pass":
            continue
        evidence = item.get("evidence", "")
        evidence_class = item.get("evidence_class")
        if expected[0] not in evidence and evidence_class not in expected[1:]:
            errors.append(f"mvp-status {name} blocker lacks fail-closed evidence detail")

    return errors


def check_larp_claim_boundaries(root: Path) -> list[str]:
    errors: list[str] = []
    sensitive_docs = [
        root / "docs/project/workstream-gap-review.md",
        root / "docs/project/critical-gap-review.md",
        root / "docs/toolchain/headless-cli-audit.md",
        root / "docs/toolchain/README.md",
        root / "docs/risks/risk-register.md",
    ]
    required_phrases = [
        "scaffold",
        "not",
        "blocked",
    ]
    for path in sensitive_docs:
        text = path.read_text(errors="ignore").lower()
        if any(phrase not in text for phrase in required_phrases):
            errors.append(f"{path.relative_to(root)} lacks scaffold/blocker boundary language")

    gap_review = (root / "docs/project/workstream-gap-review.md").read_text(errors="ignore")
    required_review_terms = [
        "Build Artifact Versus Source Evidence",
        "Reporting Blind Spots Closed Locally",
        "Remaining Tooling And Benchmark Work Order",
        "qemu_smoke.log",
        "renode_smoke.log",
        "mobile_smoke.tflite",
    ]
    for term in required_review_terms:
        if term not in gap_review:
            errors.append(f"workstream gap review missing closure term: {term}")

    return errors


def main() -> int:
    parser = ArgumentParser(description="Validate generated pipeline artifacts.")
    parser.add_argument(
        "--strict-formal", action="store_true", help="require SBY deep formal evidence"
    )
    parser.add_argument("--require-pd-signoff", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        print("Missing required pipeline artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    missing_source = [path for path in REQUIRED_SOURCE if not (root / path).is_file()]
    if missing_source:
        print("Missing required source/audit artifacts:")
        for path in missing_source:
            print(f"  - {path}")
        return 1

    yosys_log = (root / "build/reports/hello_soc_yosys.log").read_text(errors="ignore")
    if (
        "Number of cells:" not in yosys_log
        and "=== design hierarchy ===" not in yosys_log
        and (
            "End of script." not in yosys_log
            or "Dumping module `\\hello_chip_top'." not in yosys_log
        )
    ):
        print("Yosys report does not look like a completed synthesis log.")
        return 1

    netlist = (root / "build/netlist/hello_chip_synth.v").read_text(errors="ignore")
    if "module hello_chip_top" not in netlist:
        print("Synthesized netlist does not contain hello_chip_top.")
        return 1

    evidence_errors = []
    evidence_errors.extend(validate_cocotb_manifest(root))
    evidence_errors.extend(validate_formal_manifest(root, args.strict_formal))
    if evidence_errors:
        print("Pipeline evidence manifest checks failed:")
        for error in evidence_errors:
            print(f"  - {error}")
        return 1

    if args.require_pd_signoff:
        subprocess.run([sys.executable, "scripts/check_pd_signoff.py"], cwd=root, check=True)

    checks = [
        [sys.executable, "verify/check_stub_audit.py"],
        [sys.executable, "scripts/check_physical_closure_work_order.py"],
        [sys.executable, "scripts/check_real_world_gates.py"],
        [sys.executable, "scripts/check_software_bsp.py", "all", "--scaffold-only"],
        [sys.executable, "sw/check_bsp_scaffolds.py", "all"],
        [
            sys.executable,
            "benchmarks/run_benchmarks.py",
            "--dry-run",
            "--report-id",
            "pipeline-check",
        ],
        [
            sys.executable,
            "benchmarks/run_benchmarks.py",
            "validate-report",
            "benchmarks/results/pipeline-check/report.json",
        ],
        [sys.executable, "scripts/check_mvp_status.py", "--fail-on-fail"],
        [sys.executable, "scripts/check_prototype_status_dashboard.py"],
    ]
    for command in checks:
        if not run_check(root, command):
            return 1

    semantic_errors = []
    semantic_errors.extend(check_headless_audit(root))
    semantic_errors.extend(check_benchmark_report(root))
    semantic_errors.extend(check_mvp_status_semantics(root))
    semantic_errors.extend(check_larp_claim_boundaries(root))
    if semantic_errors:
        print("Pipeline semantic evidence checks failed:")
        for error in semantic_errors:
            print(f"  - {error}")
        return 1

    print("Pipeline artifact check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
