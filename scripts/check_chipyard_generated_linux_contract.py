#!/usr/bin/env python3
"""Audit generated Chipyard DTS/regmap/memmap against the Linux launch contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/chipyard/openphone_rocket"
GEN = BUILD / "generated-src"
DTS = BUILD / "openphone-hello.dts"
GEN_DTS = GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.dts"
MEMMAP = GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.memmap.json"
IMPORT_MANIFEST = BUILD / "OpenPhoneRocketConfig.manifest.json"
VERILOG = BUILD / "openphone_rocket_ap.v"
SIMULATOR = BUILD / "simulator"

REGMAPS = {
    "boot_address": GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.0x1000.0.regmap.json",
    "clint": GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.0x2000000.0.regmap.json",
    "plic": GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.0xc000000.0.regmap.json",
    "uart": GEN / "chipyard.harness.TestHarness.OpenPhoneRocketConfig.0x10020000.0.regmap.json",
}

TRANSCRIPTS = [
    ROOT / "build/evidence/cpu_ap/openphone_hello_opensbi_boot.log",
    ROOT / "build/evidence/cpu_ap/openphone_hello_linux_boot.log",
    ROOT / "build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log",
    ROOT / "build/evidence/cpu_ap/openphone_hello_isa_cache_mmu.log",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def load_json(path: Path, failures: list[str]) -> dict:
    if not path.is_file():
        failures.append(f"missing {rel(path)}")
        return {}
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError as exc:
        failures.append(f"{rel(path)} is invalid JSON: {exc}")
        return {}
    require(isinstance(data, dict), f"{rel(path)} must contain a JSON object", failures)
    return data if isinstance(data, dict) else {}


def mem_region(memmap: dict, name: str) -> tuple[int, int] | None:
    for entry in memmap.get("mapping", []):
        names = entry.get("names", []) if isinstance(entry, dict) else []
        if name not in names:
            continue
        base = entry.get("base", [])
        size = entry.get("size", [])
        if isinstance(base, list) and isinstance(size, list) and base and size:
            return int(base[0]), int(size[0])
    return None


def check_dts(failures: list[str]) -> None:
    for path in (DTS, GEN_DTS):
        require(path.is_file(), f"missing generated DTS: {rel(path)}", failures)
    if not DTS.is_file():
        return

    dts = read(DTS)
    required_tokens = [
        "/dts-v1/",
        "cpu@0",
        'compatible = "sifive,rocket0", "riscv"',
        'mmu-type = "riscv,sv39"',
        "riscv,isa",
        "zicsr",
        "zifencei",
        "memory@80000000",
        "reg = <0x80000000 0x10000000>",
        "clint@2000000",
        'compatible = "riscv,clint0"',
        "interrupt-controller@c000000",
        'compatible = "riscv,plic0"',
        "serial@10020000",
        'compatible = "sifive,uart0"',
        "stdout-path",
        "rom@10000",
        "boot-address-reg@1000",
    ]
    for token in required_tokens:
        require(token in dts, f"{rel(DTS)} missing Linux launch token: {token}", failures)
    require(
        re.search(r"timebase-frequency\s*=\s*<500000>", dts) is not None,
        f"{rel(DTS)} must expose the generated timebase-frequency",
        failures,
    )


def check_memmap(failures: list[str]) -> None:
    memmap = load_json(MEMMAP, failures)
    if not memmap:
        return

    expected = {
        "rom@10000": (0x10000, 0x10000),
        "boot-address-reg@1000": (0x1000, 0x1000),
        "clint@2000000": (0x2000000, 0x10000),
        "interrupt-controller@c000000": (0x0C000000, 0x4000000),
        "serial@10020000": (0x10020000, 0x1000),
        "memory@80000000": (0x80000000, 0x10000000),
    }
    for name, expected_region in expected.items():
        found = mem_region(memmap, name)
        require(
            found == expected_region,
            f"{rel(MEMMAP)} {name} region is {found}, expected {expected_region}",
            failures,
        )


def check_regmaps(failures: list[str]) -> None:
    required_by_regmap = {
        "boot_address": ["bitWidth"],
        "clint": ["msip_0", "mtimecmp_0", "mtime_0"],
        "plic": ["priority_1", "pending_1", "enables_0", "threshold_0", "claim_complete_0"],
        "uart": ["txdata", "rxdata", "txctrl", "rxen", "ie", "ip", "div"],
    }
    for name, path in REGMAPS.items():
        data = load_json(path, failures)
        if not data:
            continue
        text = json.dumps(data)
        for token in required_by_regmap[name]:
            require(token in text, f"{rel(path)} missing register marker: {token}", failures)


def check_import_state(failures: list[str], blockers: list[str]) -> None:
    require(VERILOG.is_file(), f"missing generated Verilog: {rel(VERILOG)}", failures)
    if VERILOG.is_file():
        text = read(VERILOG)
        require(
            "module openphone_rocket_ap" in text,
            f"{rel(VERILOG)} missing openphone_rocket_ap module",
            failures,
        )

    if not IMPORT_MANIFEST.is_file():
        blockers.append(f"missing import manifest {rel(IMPORT_MANIFEST)}")
    if not SIMULATOR.is_dir():
        blockers.append(f"missing generated simulator directory {rel(SIMULATOR)}")
    elif not any(SIMULATOR.iterdir()):
        blockers.append(f"generated simulator directory is empty: {rel(SIMULATOR)}")
    for transcript in TRANSCRIPTS:
        if not transcript.is_file():
            blockers.append(f"missing executable boot evidence {rel(transcript)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-boot-evidence", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    blockers: list[str] = []
    check_dts(failures)
    check_memmap(failures)
    check_regmaps(failures)
    check_import_state(failures, blockers)

    if failures:
        print("STATUS: FAIL chipyard.generated_linux_contract")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(
        "STATUS: PASS chipyard.generated_linux_contract - generated DTS/memmap/regmaps expose minimum Linux launch nodes"
    )
    if blockers:
        print(
            "STATUS: BLOCKED chipyard.generated_linux_boot - generated AP is not boot-evidence complete:"
        )
        for blocker in blockers:
            print(f"  - {blocker}")
        return 1 if args.require_boot_evidence else 0

    print("STATUS: PASS chipyard.generated_linux_boot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
