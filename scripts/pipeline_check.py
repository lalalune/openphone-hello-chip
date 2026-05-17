#!/usr/bin/env python3
from pathlib import Path
import re
import sys


REQUIRED = [
    "build/netlist/hello_chip_synth.v",
    "build/reports/hello_soc_yosys.log",
    "build/reports/tool_versions.txt",
    "verify/cocotb/results.xml",
    "build/verilator/Vhello_chip_top",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        print("Missing required pipeline artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    yosys_log = (root / "build/reports/hello_soc_yosys.log").read_text(errors="ignore")
    if "Number of cells:" not in yosys_log:
        print("Yosys report does not look like a completed synthesis log.")
        return 1

    netlist = (root / "build/netlist/hello_chip_synth.v").read_text(errors="ignore")
    if "module hello_chip_top" not in netlist:
        print("Synthesized netlist does not contain hello_chip_top.")
        return 1

    cocotb = (root / "verify/cocotb/results.xml").read_text(errors="ignore")
    failures = sum(int(value) for value in re.findall(r'failures="(\d+)"', cocotb))
    errors = sum(int(value) for value in re.findall(r'errors="(\d+)"', cocotb))
    testcases = re.findall(r"<testcase\b", cocotb)
    if failures or errors or not testcases:
        print("cocotb results.xml is missing a passing non-empty result.")
        return 1

    formal_logs = [
        root / "build/reports/hello_soc_top_formal_yosys.log",
        root / "build/reports/hello_npu_formal_yosys.log",
        root / "build/reports/hello_dma_formal_yosys.log",
    ]
    sby_status = [
        root / "verify/formal/hello_dbg_mmio_bridge/status",
        root / "verify/formal/hello_npu/status",
        root / "verify/formal/hello_dma/status",
        root / "verify/formal/hello_soc_top/status",
    ]
    has_yosys_fallback = all(path.is_file() for path in formal_logs)
    has_sby_pass = all(path.is_file() and "PASS" in path.read_text(errors="ignore") for path in sby_status)
    if not (has_yosys_fallback or has_sby_pass):
        print("No complete formal evidence found.")
        return 1

    print("Pipeline artifact check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
