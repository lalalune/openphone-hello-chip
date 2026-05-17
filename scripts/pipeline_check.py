#!/usr/bin/env python3
from pathlib import Path
import json
import re
import subprocess
import sys


REQUIRED = [
    "build/netlist/hello_chip_synth.v",
    "build/reports/hello_soc_yosys.log",
    "build/reports/tool_versions.txt",
    "build/reports/cocotb/manifest.json",
    "build/reports/formal_manifest.json",
    "build/verilator/Vhello_chip_top",
]

REQUIRED_SOURCE = [
    "scripts/check_software_bsp.py",
    "scripts/check_mvp_status.py",
    "scripts/check_real_world_gates.py",
    "scripts/check_physical_closure_work_order.py",
    "docs/toolchain/headless-cli-audit.md",
    "docs/toolchain/README.md",
    "docs/spec-db/mobile-sota-2026.yaml",
    "docs/benchmarks/benchmark-matrix.md",
    "docs/benchmarks/harness.md",
    "docs/benchmarks/report-schema.yaml",
    "docs/android/riscv-bringup.md",
    "docs/project/three-week-execution-plan.md",
    "docs/project/workstreams.md",
    "docs/risks/risk-register.md",
    "docs/manufacturing/real-world-verification-gaps.yaml",
    "docs/manufacturing/physical-closure-work-order.yaml",
    "benchmarks/configs/fio-rand-rw.fio",
    "benchmarks/configs/fio-seq-read.fio",
    "benchmarks/configs/benchmark_plan.json",
    "benchmarks/models/README.md",
    "benchmarks/run_benchmarks.py",
    "sw/platform/hello_platform_contract.json",
    "sw/platform/generated/hello_platform_contract.h",
    "sw/bootrom/hello_qemu_firmware.S",
    "sw/bootrom/linker.ld",
    "sw/buildroot/README.md",
    "sw/buildroot/external.desc",
    "sw/buildroot/Config.in",
    "sw/buildroot/external.mk",
    "sw/buildroot/scripts/import-buildroot-external.sh",
    "sw/buildroot/configs/openphone_hello_defconfig",
    "sw/buildroot/board/openphone/hello/linux.fragment",
    "sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke",
    "sw/linux/README.md",
    "sw/linux/scripts/import-linux-bsp.sh",
    "sw/linux/dts/openphone-hello.dts",
    "sw/linux/drivers/hello/hello_platform_contract.h",
    "sw/linux/drivers/hello/Kconfig",
    "sw/linux/drivers/hello/Makefile",
    "sw/linux/drivers/hello/hello-npu.c",
    "sw/linux/drivers/hello/hello-dma.c",
    "sw/linux/tests/hello-mmio-smoke.c",
    "sw/aosp-device/README.md",
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
    "sw/opensbi/README.md",
    "sw/u-boot/README.md",
    "sw/check_bsp_scaffolds.py",
    "verify/check_stub_audit.py",
]


def run_check(root: Path, command: list[str]) -> bool:
    result = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        print(f"Command failed: {' '.join(command)}")
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
        return False
    return True


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
    return [f"headless CLI audit missing required evidence path: {term}" for term in required_terms if term not in text]


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
        if result and result.get("status") != "blocked":
            errors.append(f"{name} must stay blocked until a real mobile_smoke.tflite artifact exists")

    return errors


def check_mvp_status_semantics(root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "scripts/check_mvp_status.py", "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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
        if item.get("status") == "pass" and item.get("evidence_class") in {"scaffold_only", "source_present", "tool_available"}:
            errors.append(f"mvp-status lets scaffold/tool/source evidence pass as implementation proof: {name}")

    for item in statuses:
        evidence = item.get("evidence", "").lower()
        if item.get("status") == "pass" and "release check failed" in evidence:
            errors.append(f"mvp-status pass row contains release failure text: {item.get('subsystem')}")

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
        and ("End of script." not in yosys_log or "Dumping module `\\hello_chip_top'." not in yosys_log)
    ):
        print("Yosys report does not look like a completed synthesis log.")
        return 1

    netlist = (root / "build/netlist/hello_chip_synth.v").read_text(errors="ignore")
    if "module hello_chip_top" not in netlist:
        print("Synthesized netlist does not contain hello_chip_top.")
        return 1

    cocotb_manifest = json.loads((root / "build/reports/cocotb/manifest.json").read_text())
    targets = cocotb_manifest.get("targets", {})
    if not isinstance(targets, dict) or not targets:
        print("cocotb manifest is missing target entries.")
        return 1
    for name, entry in targets.items():
        xml = root / entry.get("result_xml", "")
        stats = entry.get("stats", {})
        if not xml.is_file():
            print(f"cocotb {name} is missing result XML.")
            return 1
        if stats.get("failures") or stats.get("errors") or not stats.get("testcases"):
            print(f"cocotb {name} is missing a passing non-empty result.")
            return 1

    formal_evidence = {
        "hello_dbg_mmio_bridge": [
            root / "verify/formal/hello_dbg_mmio_bridge/status",
            root / "scripts/run_formal.sh",
        ],
        "hello_npu": [
            root / "verify/formal/hello_npu/status",
            root / "build/reports/hello_npu_formal_yosys.log",
        ],
        "hello_dma": [
            root / "verify/formal/hello_dma/status",
            root / "build/reports/hello_dma_formal_yosys.log",
        ],
        "hello_soc_top": [
            root / "verify/formal/hello_soc_top/status",
            root / "build/reports/hello_soc_top_formal_yosys.log",
        ],
    }
    missing_formal = []
    for name, paths in formal_evidence.items():
        status_paths = [path for path in paths if path.name == "status"]
        log_paths = [path for path in paths if path.name != "status"]
        has_sby_pass = any(path.is_file() and "PASS" in path.read_text(errors="ignore") for path in status_paths)
        has_yosys_log = any(
            path.is_file()
            and (
                path.name != "run_formal.sh"
                or "Bridge formal requires SymbiYosys" in path.read_text(errors="ignore")
            )
            for path in log_paths
        )
        if not (has_sby_pass or has_yosys_log):
            missing_formal.append(name)
    if missing_formal:
        print("No complete formal evidence found.")
        for name in missing_formal:
            print(f"  - {name}")
        return 1

    if sys.argv[1:] == ["--require-pd-signoff"]:
        subprocess.run([sys.executable, "scripts/check_pd_signoff.py"], cwd=root, check=True)

    checks = [
        [sys.executable, "verify/check_stub_audit.py"],
        [sys.executable, "scripts/check_physical_closure_work_order.py"],
        [sys.executable, "scripts/check_real_world_gates.py"],
        [sys.executable, "scripts/check_software_bsp.py", "all", "--scaffold-only"],
        [sys.executable, "sw/check_bsp_scaffolds.py", "all"],
        [sys.executable, "benchmarks/run_benchmarks.py", "--dry-run", "--report-id", "pipeline-check"],
        [
            sys.executable,
            "benchmarks/run_benchmarks.py",
            "validate-report",
            "benchmarks/results/pipeline-check/report.json",
        ],
        [sys.executable, "scripts/check_mvp_status.py", "--fail-on-fail"],
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
