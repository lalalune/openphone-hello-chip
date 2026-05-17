#!/usr/bin/env python3
"""Fail closed on silent RTL/sim/verification placeholders.

This intentionally covers only Worker A owned paths. It allows named stubs only
when they have an executable test, fail-closed behavior, or a documented blocker.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
OWNED_ROOTS = (ROOT / "rtl", ROOT / "sim", ROOT / "verify")
SKIP_PARTS = {
    "__pycache__",
    "sim_build_hello_chip_top_test_hello_chip.EkHwvK",
    "sim_build",
    "model",
    "engine_0",
    "src",
}
SKIP_SUFFIXES = {".pyc", ".sqlite", ".log", ".xml"}
TERMS = re.compile(r"\b(stub|placeholder|TODO|FIXME|not implemented|dummy|mock|scaffold)\b", re.IGNORECASE)
REQUIRED_GAP_AREAS = ("cpu", "interconnect", "display", "dma", "npu")


@dataclass(frozen=True)
class AllowedFinding:
    path: str
    pattern: str
    rationale: str


ALLOWLIST = (
    AllowedFinding(
        "rtl/bootrom/hello_bootrom.sv",
        "boot vector placeholder",
        "Boot ROM exposes a documented contract word; platform-contract checks pin it.",
    ),
    AllowedFinding(
        "rtl/cpu/hello_cpu_subsystem_stub.sv",
        "hello_cpu_subsystem_stub",
        "Executable tiny CPU model; covered by verify/cocotb/test_tiny_cpu_execution.py.",
    ),
    AllowedFinding(
        "verify/cocotb/Makefile",
        "hello_cpu_subsystem_stub",
        "Builds the executable tiny CPU model into cocotb simulations.",
    ),
    AllowedFinding(
        "verify/cocotb/hello_tiny_cpu_contract_tb.sv",
        "hello_cpu_subsystem_stub",
        "Testbench instantiates the executable tiny CPU model.",
    ),
    AllowedFinding(
        "sim/qemu/README.md",
        "--build-stub",
        "QEMU README documents the compatibility alias while the preferred path is firmware.",
    ),
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def allowed(path: Path, line: str) -> str | None:
    path_s = rel(path)
    for finding in ALLOWLIST:
        if finding.path == path_s and finding.pattern.lower() in line.lower():
            return finding.rationale
    return None


def iter_files() -> list[Path]:
    paths: list[Path] = []
    for root in OWNED_ROOTS:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() == Path(__file__).resolve():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix in SKIP_SUFFIXES:
                continue
            paths.append(path)
    return sorted(paths)


def check_placeholder_terms() -> list[str]:
    errors: list[str] = []
    inventory: list[str] = []
    for path in iter_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, start=1):
            if not TERMS.search(line):
                continue
            rationale = allowed(path, line)
            if rationale is None:
                errors.append(f"{rel(path)}:{lineno}: silent placeholder term: {line.strip()}")
            else:
                inventory.append(f"{rel(path)}:{lineno}: {rationale}")

    print("Allowed placeholder/stub inventory:")
    for item in inventory:
        print(f"  - {item}")
    return errors


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_renode_scaffold() -> list[str]:
    errors: list[str] = []
    readme = (ROOT / "sim/renode/README.md").read_text(encoding="utf-8").lower()
    repl = (ROOT / "sim/renode/openphone_hello.repl").read_text(encoding="utf-8").lower()
    resc = (ROOT / "sim/renode/openphone_hello.resc").read_text(encoding="utf-8").lower()

    require("qemu-virt reference target" in readme, "Renode README must label the flow as qemu-virt reference.", errors)
    require("not the hello-chip hardware abi" in readme, "Renode README must state this is not the hello-chip hardware ABI.", errors)
    require("0x80000000" in repl and "0x100000" in repl, "Renode REPL must define RAM at the qemu-virt load window.", errors)
    require("0x10000000" in repl and "litex_uart" in repl, "Renode REPL must define the qemu-virt UART window.", errors)
    require("loadplatformdescription" in resc and "openphone_hello.repl" in resc, "Renode RESC must load the checked-in REPL.", errors)
    require("start" in resc, "Renode RESC must start the machine explicitly.", errors)
    return errors


def check_gap_work_order() -> list[str]:
    errors: list[str] = []
    path = ROOT / "verify/rtl_gap_work_order.yaml"
    require(path.exists(), "RTL gap work order must exist at verify/rtl_gap_work_order.yaml.", errors)
    if errors:
        return errors

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "RTL gap work order must be a YAML mapping.", errors)
    if not isinstance(data, dict):
        return errors

    require(data.get("fail_closed_required") is True, "RTL gap work order must require fail-closed behavior.", errors)
    areas = data.get("areas")
    require(isinstance(areas, dict), "RTL gap work order must define an areas mapping.", errors)
    if not isinstance(areas, dict):
        return errors

    for area in REQUIRED_GAP_AREAS:
        entry = areas.get(area)
        require(isinstance(entry, dict), f"RTL gap work order missing area: {area}.", errors)
        if not isinstance(entry, dict):
            continue
        require(bool(entry.get("current_posture")), f"{area} must describe current_posture.", errors)
        require(bool(entry.get("fail_closed")), f"{area} must list fail_closed behavior.", errors)
        require(bool(entry.get("checks")), f"{area} must list executable checks.", errors)
        gaps = entry.get("critical_gaps")
        require(isinstance(gaps, list) and bool(gaps), f"{area} must list critical_gaps.", errors)
        if not isinstance(gaps, list):
            continue
        for gap in gaps:
            require(isinstance(gap, dict), f"{area} critical_gaps entries must be mappings.", errors)
            if not isinstance(gap, dict):
                continue
            require(gap.get("status") == "open", f"{area}:{gap.get('id', '<missing>')} must remain status=open until closed by RTL and checks.", errors)
            require(bool(gap.get("work_order")), f"{area}:{gap.get('id', '<missing>')} must include work_order.", errors)
    return errors


def main() -> int:
    errors = check_placeholder_terms()
    errors.extend(check_renode_scaffold())
    errors.extend(check_gap_work_order())

    if errors:
        print("Stub audit failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Stub audit passed: no silent owned RTL/sim/verification placeholders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
