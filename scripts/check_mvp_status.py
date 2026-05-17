#!/usr/bin/env python3
"""Report MVP subsystem status with explicit pass/block/fail evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = "PASS"
BLOCK = "BLOCK"
FAIL = "FAIL"


@dataclass
class Status:
    subsystem: str
    status: str
    evidence: str
    next_step: str
    evidence_class: str = "unspecified"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def command_status(subsystem: str, command: list[str], next_step: str) -> Status:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = " ".join(line.strip() for line in result.stdout.splitlines() if line.strip())
    evidence = output[:220] if output else "command produced no output"
    if (
        "release check failed:" in result.stdout
        or "release gate remains blocked" in result.stdout
        or "explicitly blocked" in result.stdout
    ):
        return Status(subsystem, BLOCK, evidence, next_step, "release_blocker")
    if "BLOCKED:" in result.stdout:
        return Status(subsystem, BLOCK, evidence, next_step, "tool_blocker")
    if result.returncode == 0:
        return Status(subsystem, PASS, evidence, "none", "command_pass")
    return Status(subsystem, FAIL, evidence, next_step, "command_fail")


def software_bsp_status() -> Status:
    result = subprocess.run(
        [sys.executable, "scripts/check_software_bsp.py", "all", "--scaffold-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = " ".join(line.strip() for line in result.stdout.splitlines() if line.strip())
    evidence = output[:220] if output else "command produced no output"
    if result.returncode != 0:
        return Status("software-bsp", FAIL, evidence, "make software-bsp-check", "command_fail")
    if "external evidence blocked" in result.stdout:
        return Status(
            "software-bsp", BLOCK, evidence, "make software-bsp-evidence-check", "scaffold_only"
        )
    return Status("software-bsp", PASS, evidence, "none", "command_pass")


def cpu_ap_status() -> Status:
    result = subprocess.run(
        [sys.executable, "scripts/check_cpu_ap_completion_gate.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    evidence = " ".join(lines)[:220] if lines else "command produced no output"
    if any(line.startswith("STATUS: PASS cpu_ap.completion_gate") for line in lines):
        return Status("cpu-ap", PASS, evidence, "none", "generated_artifact")
    if any(line.startswith("STATUS: BLOCKED cpu_ap.completion_gate") for line in lines):
        return Status(
            "cpu-ap",
            BLOCK,
            evidence,
            "make chipyard-generated-check cpu-ap-evidence-check cpu-ap-completion-gate",
            "release_blocker",
        )
    return Status("cpu-ap", FAIL, evidence, "make cpu-ap-completion-gate", "claim_gate_fail")


def status_check(subsystem: str, command: list[str], pass_marker: str, next_step: str) -> Status:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    evidence = " ".join(lines)[:220] if lines else "command produced no output"
    status_lines = [line for line in lines if line.startswith("STATUS: ")]

    if any(line.startswith("STATUS: FAIL ") for line in status_lines) or result.returncode == 1:
        return Status(subsystem, FAIL, evidence, next_step, "test_fail")
    if any(pass_marker in line for line in status_lines):
        return Status(subsystem, PASS, evidence, "none", "generated_artifact")
    if any(line.startswith("STATUS: BLOCKED ") for line in status_lines) or result.returncode == 2:
        return Status(subsystem, BLOCK, evidence, next_step, "tool_blocker")
    if result.returncode == 0:
        return Status(subsystem, BLOCK, evidence, next_step, "scaffold_only")
    return Status(subsystem, FAIL, evidence, next_step, "command_fail")


def files_status(subsystem: str, paths: list[str], pass_evidence: str, next_step: str) -> Status:
    missing = [path for path in paths if not (ROOT / path).exists()]
    if missing:
        return Status(
            subsystem,
            BLOCK,
            "missing source/config artifacts: " + ", ".join(missing),
            next_step,
            "missing_source",
        )
    return Status(subsystem, PASS, pass_evidence, "none", "source_present")


def tool_path(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def riscv_elf_toolchain() -> str | None:
    found = tool_path("riscv64-unknown-elf-gcc", "riscv64-elf-gcc", "riscv64-linux-gnu-gcc")
    if found:
        return found

    for candidate in ("/opt/homebrew/opt/llvm/bin/clang", "clang"):
        found = str(Path(candidate)) if Path(candidate).is_file() else shutil.which(candidate)
        if not found:
            continue
        result = subprocess.run(
            [
                found,
                "--target=riscv64-unknown-elf",
                "-fuse-ld=lld",
                "-x",
                "assembler",
                "-c",
                "/dev/null",
                "-o",
                "/tmp/openphone-riscv-toolchain-test.o",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        Path("/tmp/openphone-riscv-toolchain-test.o").unlink(missing_ok=True)
        if result.returncode == 0:
            return found
    return None


def artifact_status(
    subsystem: str,
    artifacts: list[str],
    tool_names: tuple[str, ...],
    command: str,
    blocked_text: str,
) -> Status:
    missing = [path for path in artifacts if not (ROOT / path).is_file()]
    if not missing:
        return Status(
            subsystem,
            PASS,
            "generated artifacts present: " + ", ".join(artifacts),
            "none",
            "generated_artifact",
        )
    found = tool_path(*tool_names)
    if found:
        return Status(
            subsystem,
            BLOCK,
            "missing regenerated artifacts; tool available at " + found + ": " + ", ".join(missing),
            command,
            "regen_required",
        )
    return Status(
        subsystem,
        BLOCK,
        blocked_text + "; missing generated artifacts: " + ", ".join(missing),
        command,
        "tool_blocker",
    )


def toolchain_status() -> Status:
    required = ["python3", "make", "git"]
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        return Status(
            "toolchain-fast-path",
            FAIL,
            "missing required tools: " + ", ".join(missing),
            "make tools",
            "tool_blocker",
        )

    optional_blocks = []
    for group, tools in {
        "rtl": ("verilator", "iverilog"),
        "synth/formal": ("yosys",),
        "qemu": ("qemu-system-riscv64",),
        "renode": ("renode",),
        "pd": ("openlane", "flow.tcl", "docker"),
    }.items():
        if tool_path(*tools) is None:
            optional_blocks.append(group)
    if riscv_elf_toolchain() is None:
        optional_blocks.append("riscv-elf")

    evidence = "required host tools found"
    if optional_blocks:
        return Status(
            "toolchain-fast-path",
            BLOCK,
            evidence + "; blocked optional gates: " + ", ".join(optional_blocks),
            "scripts/check_tools.sh && scripts/tool_versions.sh",
            "tool_blocker",
        )
    return Status("toolchain-fast-path", PASS, evidence, "none", "tool_available")


def cocotb_status() -> Status:
    manifest = ROOT / "build/reports/cocotb/manifest.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        targets = data.get("targets", {}) if isinstance(data, dict) else {}
        if isinstance(targets, dict) and targets:
            for entry in targets.values():
                stats = entry.get("stats", {}) if isinstance(entry, dict) else {}
                if stats.get("failures") or stats.get("errors") or not stats.get("testcases"):
                    return Status(
                        "cocotb",
                        FAIL,
                        "cocotb manifest records failures/errors or no testcase",
                        "make cocotb",
                        "test_fail",
                    )
            return Status(
                "cocotb",
                PASS,
                "per-target cocotb XML artifacts have passing testcases under build/reports/cocotb",
                "none",
                "generated_artifact",
            )

    result = ROOT / "verify/cocotb/results.xml"
    if not result.is_file():
        return Status(
            "cocotb",
            BLOCK,
            "missing regenerated cocotb manifest or legacy results.xml",
            "make cocotb",
            "regen_required",
        )
    text = result.read_text(errors="ignore")
    if "<failure" in text or "<error" in text or "<testcase" not in text:
        return Status(
            "cocotb",
            FAIL,
            "results.xml contains failures/errors or no testcase",
            "make cocotb",
            "test_fail",
        )
    return Status(
        "cocotb",
        PASS,
        "generated artifact verify/cocotb/results.xml has passing testcases",
        "none",
        "generated_artifact",
    )


def formal_status() -> Status:
    sby_status = [
        ROOT / "verify/formal/hello_dbg_mmio_bridge/status",
        ROOT / "verify/formal/hello_npu/status",
        ROOT / "verify/formal/hello_dma/status",
        ROOT / "verify/formal/hello_soc_top/status",
    ]
    fallback_logs = [
        ROOT / "build/reports/hello_soc_top_formal_yosys.log",
        ROOT / "build/reports/hello_npu_formal_yosys.log",
        ROOT / "build/reports/hello_dma_formal_yosys.log",
    ]
    if all(path.is_file() and "PASS" in path.read_text(errors="ignore") for path in sby_status):
        return Status(
            "formal",
            PASS,
            "generated SymbiYosys status files report PASS",
            "none",
            "generated_artifact",
        )
    failed_status = [
        rel(path)
        for path in sby_status
        if path.is_file()
        and any(token in path.read_text(errors="ignore") for token in ("FAIL", "ERROR"))
    ]
    failed_status.extend(
        rel(path.parent / "ERROR") for path in sby_status if (path.parent / "ERROR").is_file()
    )
    if failed_status:
        return Status(
            "formal",
            FAIL,
            "SymbiYosys status file reports failure: " + ", ".join(failed_status),
            "make formal",
            "test_fail",
        )
    if all(path.is_file() for path in fallback_logs):
        return Status(
            "formal",
            PASS,
            "generated Yosys formal fallback logs present",
            "none",
            "generated_artifact",
        )
    if tool_path("sby", "yosys"):
        return Status(
            "formal", BLOCK, "missing regenerated formal evidence", "make formal", "regen_required"
        )
    return Status(
        "formal",
        BLOCK,
        "formal tools and generated evidence missing",
        "make formal inside Docker/Nix",
        "tool_blocker",
    )


def qemu_status() -> Status:
    status = status_check(
        "qemu",
        ["scripts/run_qemu.sh", "--check"],
        "STATUS: PASS qemu.check",
        "make qemu-check",
    )
    if status.status == PASS:
        smoke_log = ROOT / "build/reports/qemu_smoke.log"
        if not smoke_log.is_file() or "openphone hello qemu" not in smoke_log.read_text(
            errors="ignore"
        ):
            return Status(
                "qemu",
                BLOCK,
                "qemu.check passed but build/reports/qemu_smoke.log is missing the required banner",
                "make qemu-check",
                "regen_required",
            )
    return status


def renode_status() -> Status:
    return status_check(
        "renode",
        ["scripts/run_renode.sh", "--check"],
        "STATUS: PASS renode.check",
        "make renode-check",
    )


def qemu_os_status() -> Status:
    status = status_check(
        "qemu-os-boot",
        ["scripts/run_qemu.sh", "--check-os"],
        "STATUS: PASS qemu.os_boot",
        "make qemu-os-check",
    )
    if status.status == PASS:
        return Status(
            "qemu-virt-os-boot",
            PASS,
            status.evidence + " (reference qemu-virt only; not OS on generated OpenPhone AP)",
            "none",
            "reference_qemu_virt",
        )
    if status.status == BLOCK:
        return Status(
            "qemu-virt-os-boot",
            BLOCK,
            status.evidence,
            "build/import a Linux Image and initrd/rootfs, then run make qemu-os-check",
            "missing_os_payload",
        )
    return status


def on_chip_os_status() -> Status:
    report = ROOT / "build/reports/mvp_simulator.json"
    if report.is_file():
        try:
            data = json.loads(report.read_text())
        except json.JSONDecodeError:
            return Status(
                "our-chip-os-boot",
                FAIL,
                "build/reports/mvp_simulator.json is invalid JSON",
                "python3 scripts/run_mvp_simulator.py",
                "report_fail",
            )
        if data.get("on_chip_os_boot_claim") is True:
            return Status(
                "our-chip-os-boot",
                PASS,
                "MVP simulator report records on_chip_os_boot_claim true",
                "none",
                "generated_ap_os_boot",
            )
        blockers = []
        for item in data.get("blockers_to_on_chip_os_boot", []):
            if isinstance(item, dict) and item.get("name"):
                blockers.append(str(item["name"]))
        detail = ", ".join(blockers) if blockers else "generated AP/Linux evidence not present"
        return Status(
            "our-chip-os-boot",
            BLOCK,
            "OS is not running on generated OpenPhone AP/hello-chip RTL; blockers: " + detail,
            "python3 scripts/run_mvp_simulator.py && make mvp-simulator-check",
            "release_blocker",
        )
    return Status(
        "our-chip-os-boot",
        BLOCK,
        "missing build/reports/mvp_simulator.json; cannot claim OS on generated OpenPhone AP",
        "python3 scripts/run_mvp_simulator.py && make mvp-simulator-check",
        "missing_report",
    )


def android_sim_status() -> Status:
    result = subprocess.run(
        [sys.executable, "scripts/check_android_sim_boot.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    evidence = " ".join(lines)[:220] if lines else "command produced no output"
    if result.returncode == 0:
        return Status("android-sim", PASS, evidence, "none", "generated_artifact")
    if result.returncode == 2:
        return Status(
            "android-sim",
            BLOCK,
            evidence,
            "AOSP_DIR=/path/to/aosp scripts/boot_android_simulator.sh --run-cuttlefish",
            "external_aosp_blocker",
        )
    return Status(
        "android-sim", FAIL, evidence, "python3 scripts/check_android_sim_boot.py", "test_fail"
    )


def benchmark_status() -> Status:
    npu_proof = ROOT / "benchmarks/capabilities/hello_npu_nnapi.proof.json"
    if not npu_proof.is_file():
        return Status(
            "benchmarks",
            BLOCK,
            "hello-NPU NNAPI capability proof is missing; fail-closed dry-run planning evidence "
            "only until real benchmark evidence exists; host-smoke benchmark reports cannot "
            "satisfy MVP NPU benchmark evidence",
            "python3 benchmarks/run_benchmarks.py plan --bench tflite_hello_npu --strict-missing",
            "scaffold_only",
        )

    reports = sorted(
        (ROOT / "benchmarks/results").glob("*/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    report = ROOT / "benchmarks/results/pipeline-check/report.json"
    for candidate in reports:
        try:
            if json.loads(candidate.read_text()).get("dry_run") is not True:
                report = candidate
                break
        except (OSError, json.JSONDecodeError):
            continue
    else:
        report = reports[0] if reports else report
    if not report.is_file():
        return Status(
            "benchmarks",
            BLOCK,
            "missing regenerated pipeline dry-run report",
            "make benchmarks-dry-run",
            "regen_required",
        )
    data = json.loads(report.read_text())
    statuses = {result.get("status") for result in data.get("results", [])}
    if "failed" in statuses or "error" in statuses or "timeout" in statuses:
        return Status(
            "benchmarks",
            FAIL,
            "report has failing benchmark status",
            "python3 benchmarks/run_benchmarks.py validate-report " + rel(report),
            "test_fail",
        )
    if data.get("dry_run") is True:
        return Status(
            "benchmarks",
            BLOCK,
            "benchmark report is dry-run planning evidence only: " + rel(report),
            "python3 benchmarks/run_benchmarks.py --strict-missing",
            "scaffold_only",
        )
    if (
        "blocked" in statuses
        or "planned_missing_deps" in statuses
        or "missing_dependencies" in statuses
    ):
        missing = []
        for result in data.get("results", []):
            for item in result.get("missing_dependency_details", []):
                missing.append(f"{result.get('name')}.{item.get('name')}:{item.get('reason')}")
            for item in result.get("blocked_assets", []):
                missing.append(f"{result.get('name')}.{item.get('name')}:{item.get('reason')}")
        detail = "; missing/blockers: " + ", ".join(sorted(set(missing))) if missing else ""
        return Status(
            "benchmarks",
            BLOCK,
            "benchmark report records blocked/missing benchmark dependencies: "
            + rel(report)
            + detail,
            "make benchmarks",
            "tool_blocker",
        )
    non_release_deps = []
    for result in data.get("results", []):
        for dependency in result.get("dependencies", []):
            if (
                dependency.get("release_claim_allowed") is False
                or dependency.get("evidence_kind") == "host_smoke_tool"
            ):
                non_release_deps.append(
                    f"{result.get('name')}.{dependency.get('name')}:"
                    f"{dependency.get('evidence_kind', 'non_release_dependency')}"
                )
    if non_release_deps:
        return Status(
            "benchmarks",
            BLOCK,
            "benchmark report is host-smoke/developer evidence only and cannot satisfy MVP "
            "real benchmark evidence: "
            + rel(report)
            + "; non-release deps: "
            + ", ".join(sorted(set(non_release_deps))[:8]),
            "python3 benchmarks/run_benchmarks.py --strict-missing",
            "scaffold_only",
        )
    return Status(
        "benchmarks",
        PASS,
        "benchmark report records executed results with no blocked entries: " + rel(report),
        "none",
        "generated_artifact",
    )


def product_status() -> Status:
    result = subprocess.run(
        [sys.executable, "scripts/product_check.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    evidence = " ".join(lines)[:220] if lines else "command produced no output"
    if "product release check failed:" in result.stdout:
        return Status(
            "product-package",
            BLOCK,
            evidence,
            "python3 scripts/product_check.py --release; python3 scripts/check_board_package_evidence.py --release; python3 scripts/check_pd_signoff.py",
            "release_blocker",
        )
    if result.returncode == 0:
        return Status("product-package", PASS, evidence, "none", "command_pass")
    return Status("product-package", FAIL, evidence, "make product-check", "command_fail")


def collect_statuses() -> list[Status]:
    return [
        command_status(
            "docs-and-project-plan",
            [sys.executable, "scripts/check_project_plan.py"],
            "make project-plan-check",
        ),
        command_status(
            "architecture-docs", [sys.executable, "scripts/docs_check.py"], "make docs-check"
        ),
        toolchain_status(),
        command_status(
            "platform-contract",
            [sys.executable, "scripts/check_platform_contract.py"],
            "make platform-contract-check",
        ),
        cpu_ap_status(),
        software_bsp_status(),
        command_status(
            "real-world-release-gates",
            [sys.executable, "scripts/check_real_world_gates.py"],
            "make real-world-gates-check",
        ),
        files_status(
            "rtl-source",
            [
                "rtl/top/hello_chip_top.sv",
                "rtl/top/hello_soc_top.sv",
                "rtl/npu/hello_npu.sv",
                "rtl/dma/hello_dma.sv",
            ],
            "core RTL sources present",
            "make rtl-check",
        ),
        artifact_status(
            "synthesis",
            ["build/netlist/hello_chip_synth.v", "build/reports/hello_soc_yosys.log"],
            ("yosys",),
            "make synth",
            "Yosys missing or synth evidence not generated",
        ),
        cocotb_status(),
        artifact_status(
            "verilator",
            ["build/verilator/Vhello_chip_top"],
            ("verilator",),
            "make verilator",
            "Verilator missing or harness not built",
        ),
        formal_status(),
        qemu_status(),
        qemu_os_status(),
        on_chip_os_status(),
        renode_status(),
        android_sim_status(),
        command_status(
            "pd-contract",
            [sys.executable, "scripts/check_pd_preflight.py"],
            "make pd-contract-check",
        ),
        product_status(),
        benchmark_status(),
        artifact_status(
            "release-pipeline",
            ["build/reports/tool_versions.txt"],
            ("python3",),
            "make tool-versions pipeline-check",
            "tool version report missing",
        ),
    ]


def print_text(statuses: list[Status]) -> None:
    print(f"{'STATUS':<6} {'SUBSYSTEM':<24} EVIDENCE")
    print(f"{'------':<6} {'---------':<24} --------")
    for item in statuses:
        print(f"{item.status:<6} {item.subsystem:<24} {item.evidence}")
        if item.next_step != "none":
            print(f"{'':<6} {'next':<24} {item.next_step}")


def print_json(statuses: list[Status]) -> None:
    payload = [
        {
            "subsystem": item.subsystem,
            "status": item.status.lower(),
            "evidence": item.evidence,
            "evidence_class": item.evidence_class,
            "next_step": item.next_step,
        }
        for item in statuses
    ]
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on FAIL or BLOCK")
    parser.add_argument("--fail-on-fail", action="store_true", help="Return non-zero only on FAIL")
    args = parser.parse_args(argv)

    statuses = collect_statuses()
    if args.json:
        print_json(statuses)
    else:
        print_text(statuses)

    has_fail = any(item.status == FAIL for item in statuses)
    has_block = any(item.status == BLOCK for item in statuses)
    if has_fail:
        return 1
    if args.strict and has_block:
        return 2
    if args.fail_on_fail and has_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
