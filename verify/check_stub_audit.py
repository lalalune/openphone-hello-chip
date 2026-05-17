#!/usr/bin/env python3
"""Fail closed on silent RTL/sim/verification placeholders.

This intentionally covers only Worker I owned paths. It allows named stubs only
when they have an executable test, fail-closed behavior, or a documented blocker.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OWNED_ROOTS = (ROOT / "rtl", ROOT / "sim", ROOT / "verify")
SKIP_PARTS = {
    "__pycache__",
    "sim_build_hello_chip_top_test_hello_chip.EkHwvK",
    "model",
    "engine_0",
    "src",
}
SKIP_SUFFIXES = {".pyc", ".sqlite", ".log", ".xml"}
TERMS = re.compile(r"\b(stub|placeholder|TODO|FIXME|not implemented|dummy|mock)\b", re.IGNORECASE)


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
        "hello_qemu_stub",
        "QEMU target is a qemu-virt reference with semantic checks and blocked-smoke wording.",
    ),
    AllowedFinding(
        "sim/qemu/README.md",
        "--build-stub",
        "QEMU README documents the explicit firmware build command for the bounded smoke.",
    ),
    AllowedFinding(
        "sim/qemu/README.md",
        "builds the stub",
        "QEMU README states when the executable smoke is attempted and when it is blocked.",
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


def main() -> int:
    errors = check_placeholder_terms()
    errors.extend(check_renode_scaffold())

    if errors:
        print("Stub audit failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Stub audit passed: no silent owned RTL/sim/verification placeholders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
