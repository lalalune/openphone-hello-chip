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
    if result.returncode == 0:
        return Status(subsystem, PASS, evidence, "none")
    return Status(subsystem, FAIL, evidence, next_step)


def files_status(subsystem: str, paths: list[str], pass_evidence: str, next_step: str) -> Status:
    missing = [path for path in paths if not (ROOT / path).exists()]
    if missing:
        return Status(subsystem, BLOCK, "missing: " + ", ".join(missing), next_step)
    return Status(subsystem, PASS, pass_evidence, "none")


def tool_path(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
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
        return Status(subsystem, PASS, "artifacts present: " + ", ".join(artifacts), "none")
    found = tool_path(*tool_names)
    if found:
        return Status(subsystem, BLOCK, "missing artifacts: " + ", ".join(missing), command)
    return Status(
        subsystem,
        BLOCK,
        blocked_text + "; missing artifacts: " + ", ".join(missing),
        command,
    )


def toolchain_status() -> Status:
    required = ["python3", "make", "git"]
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        return Status("toolchain-fast-path", FAIL, "missing required tools: " + ", ".join(missing), "make tools")

    optional_blocks = []
    for group, tools in {
        "rtl": ("verilator", "iverilog"),
        "synth/formal": ("yosys",),
        "qemu": ("qemu-system-riscv64",),
        "riscv-elf": ("riscv64-unknown-elf-gcc", "riscv64-elf-gcc", "riscv64-linux-gnu-gcc"),
        "renode": ("renode",),
        "pd": ("openlane", "flow.tcl", "docker"),
    }.items():
        if tool_path(*tools) is None:
            optional_blocks.append(group)

    evidence = "required host tools found"
    if optional_blocks:
        return Status(
            "toolchain-fast-path",
            BLOCK,
            evidence + "; blocked optional gates: " + ", ".join(optional_blocks),
            "scripts/check_tools.sh && scripts/tool_versions.sh",
        )
    return Status("toolchain-fast-path", PASS, evidence, "none")


def cocotb_status() -> Status:
    result = ROOT / "verify/cocotb/results.xml"
    if not result.is_file():
        return Status("cocotb", BLOCK, "missing verify/cocotb/results.xml", "make cocotb")
    text = result.read_text(errors="ignore")
    if "<failure" in text or "<error" in text or "<testcase" not in text:
        return Status("cocotb", FAIL, "results.xml contains failures/errors or no testcase", "make cocotb")
    return Status("cocotb", PASS, "verify/cocotb/results.xml has passing testcases", "none")


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
        return Status("formal", PASS, "SymbiYosys status files report PASS", "none")
    failed_status = [
        rel(path)
        for path in sby_status
        if path.is_file() and any(token in path.read_text(errors="ignore") for token in ("FAIL", "ERROR"))
    ]
    failed_status.extend(
        rel(path.parent / "ERROR")
        for path in sby_status
        if (path.parent / "ERROR").is_file()
    )
    if failed_status:
        return Status("formal", FAIL, "SymbiYosys status file reports failure: " + ", ".join(failed_status), "make formal")
    if all(path.is_file() for path in fallback_logs):
        return Status("formal", PASS, "Yosys formal fallback logs present", "none")
    if tool_path("sby", "yosys"):
        return Status("formal", BLOCK, "formal evidence missing", "make formal")
    return Status("formal", BLOCK, "formal tools and evidence missing", "make formal inside Docker/Nix")


def qemu_status() -> Status:
    required = [
        "sw/bootrom/hello_qemu_firmware.S",
        "sw/bootrom/linker.ld",
        "sim/qemu/README.md",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        return Status("qemu", FAIL, "missing qemu scaffold: " + ", ".join(missing), "make qemu-check")
    if not tool_path("qemu-system-riscv64") or not tool_path(
        "riscv64-unknown-elf-gcc", "riscv64-elf-gcc", "riscv64-linux-gnu-gcc"
    ):
        return Status("qemu", BLOCK, "semantic scaffold present; QEMU or RISC-V ELF compiler missing", "make qemu-check")
    return Status("qemu", PASS, "QEMU and RISC-V ELF toolchain found", "make qemu-check")


def renode_status() -> Status:
    required = ["sim/renode/openphone_hello.repl", "sim/renode/openphone_hello.resc", "sim/renode/README.md"]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        return Status("renode", FAIL, "missing Renode scaffold: " + ", ".join(missing), "make renode-check")
    if not tool_path("renode"):
        return Status("renode", BLOCK, "Renode scaffold present; renode executable missing", "make renode-check")
    return Status("renode", PASS, "Renode executable and scaffold present", "make renode-check")


def benchmark_status() -> Status:
    report = ROOT / "benchmarks/results/pipeline-check/report.json"
    if not report.is_file():
        return Status("benchmarks", BLOCK, "missing pipeline dry-run report", "make benchmarks-dry-run")
    data = json.loads(report.read_text())
    statuses = {result.get("status") for result in data.get("results", [])}
    if "failed" in statuses or "error" in statuses or "timeout" in statuses:
        return Status("benchmarks", FAIL, "report has failing benchmark status", "python3 benchmarks/run_benchmarks.py validate-report " + rel(report))
    if "blocked" in statuses or "planned_missing_deps" in statuses or "missing_dependencies" in statuses:
        return Status("benchmarks", BLOCK, "dry-run report records blocked/missing benchmark dependencies", "make benchmarks")
    return Status("benchmarks", PASS, "benchmark dry-run report has no blocked entries", "none")


def collect_statuses() -> list[Status]:
    return [
        command_status("docs-and-project-plan", [sys.executable, "scripts/check_project_plan.py"], "make project-plan-check"),
        command_status("architecture-docs", [sys.executable, "scripts/docs_check.py"], "make docs-check"),
        toolchain_status(),
        command_status("platform-contract", [sys.executable, "scripts/check_platform_contract.py"], "make platform-contract-check"),
        command_status("software-bsp", [sys.executable, "scripts/check_software_bsp.py", "all"], "make software-bsp-check"),
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
        renode_status(),
        command_status("pd-contract", [sys.executable, "scripts/check_pd_preflight.py"], "make pd-contract-check"),
        command_status("product-package", [sys.executable, "scripts/product_check.py"], "make product-check"),
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
