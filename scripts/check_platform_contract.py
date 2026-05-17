#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "sw/platform/hello_platform_contract.json"
GENERATED_HEADER = ROOT / "sw/platform/generated/hello_platform_contract.h"


REGION_RTL_NAMES = {
    "bootrom": "boot_rom",
    "periph": "peripheral_control",
    "dma": "dma",
    "npu": "npu",
    "display": "display",
}

MODULE_BY_REGION = {
    "peripheral_control": ROOT / "rtl/peripherals/hello_peripherals.sv",
    "dma": ROOT / "rtl/dma/hello_dma.sv",
    "npu": ROOT / "rtl/npu/hello_npu.sv",
    "display": ROOT / "rtl/display/hello_display.sv",
}


def h(value: str) -> int:
    return int(value.replace("_", ""), 16)


def fmt_hex(value: int, width: int = 8) -> str:
    return f"0x{value:0{width}X}"


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def regions_by_name(contract: dict) -> dict:
    return {region["name"]: region for region in contract["hello_chip"]["regions"]}


def generate_header(contract: dict) -> str:
    hello = contract["hello_chip"]
    qemu = contract["qemu_virt"]
    regions = regions_by_name(contract)
    boot_words = {word["name"]: h(word["value"]) for word in hello["boot_rom"]["words"]}

    lines = [
        "/* Generated from sw/platform/hello_platform_contract.json. */",
        "#ifndef HELLO_PLATFORM_CONTRACT_H",
        "#define HELLO_PLATFORM_CONTRACT_H",
        "",
        f"#define HELLO_CONTRACT_VERSION {contract['contract']['version']}u",
        f"#define HELLO_UNMAPPED_READ_VALUE {fmt_hex(h(hello['unmapped_read_value']))}u",
        f"#define HELLO_IMPLEMENTED_WINDOW_BYTES {hello['implemented_window_bytes']}u",
        "",
        f"#define HELLO_BOOT_ROM_BASE {fmt_hex(h(hello['boot_rom']['base']))}u",
        f"#define HELLO_BOOT_ROM_SIZE {fmt_hex(h(hello['boot_rom']['size']))}u",
        f"#define HELLO_BOOT_MAGIC0 {fmt_hex(boot_words['magic0'])}u",
        f"#define HELLO_BOOT_MAGIC1 {fmt_hex(boot_words['magic1'])}u",
        f"#define HELLO_BOOT_VECTOR_PLACEHOLDER {fmt_hex(boot_words['boot_vector_placeholder'])}u",
        "",
        f"#define HELLO_PERIPHERAL_CONTROL_BASE {fmt_hex(h(regions['peripheral_control']['base']))}u",
        f"#define HELLO_DMA_BASE {fmt_hex(h(regions['dma']['base']))}u",
        f"#define HELLO_NPU_BASE {fmt_hex(h(regions['npu']['base']))}u",
        f"#define HELLO_DISPLAY_BASE {fmt_hex(h(regions['display']['base']))}u",
        "",
    ]

    prefix_by_region = {
        "peripheral_control": "HELLO_PERIPH",
        "dma": "HELLO_DMA",
        "npu": "HELLO_NPU",
        "display": "HELLO_DISPLAY",
    }
    for region_name in ("peripheral_control", "dma", "npu", "display"):
        prefix = prefix_by_region[region_name]
        for reg in regions[region_name]["registers"]:
            lines.append(f"#define {prefix}_{reg['name']}_OFFSET {fmt_hex(h(reg['offset']), 2)}u")
        lines.append("")

    lines.extend(
        [
            f"#define HELLO_QEMU_VIRT_LOAD_ADDRESS {fmt_hex(h(qemu['load_address']))}u",
            f"#define HELLO_QEMU_VIRT_UART_BASE {fmt_hex(h(qemu['uart_base']))}u",
            "",
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def check_generated_header(contract: dict, errors: list[str]) -> None:
    expected = generate_header(contract)
    if not GENERATED_HEADER.is_file():
        errors.append(f"{GENERATED_HEADER.relative_to(ROOT)} is missing")
        return
    actual = GENERATED_HEADER.read_text()
    if actual != expected:
        errors.append(
            f"{GENERATED_HEADER.relative_to(ROOT)} is stale; regenerate it from "
            f"{CONTRACT_PATH.relative_to(ROOT)}"
        )


def check_bootrom_against_rtl(contract: dict, errors: list[str]) -> None:
    rtl = read_text(ROOT / "rtl/bootrom/hello_bootrom.sv")
    rtl_words = {
        int(index, 16) * 4: h(value)
        for index, value in re.findall(r"6'h([0-9A-Fa-f]+):\s*rdata\s*=\s*32'h([0-9A-Fa-f_]+)", rtl)
    }
    for word in contract["hello_chip"]["boot_rom"]["words"]:
        offset = h(word["offset"])
        expected = h(word["value"])
        actual = rtl_words.get(offset)
        require(
            actual == expected,
            f"boot ROM {word['name']} at {fmt_hex(offset, 2)} is {fmt_hex(actual or 0)}, "
            f"contract expects {fmt_hex(expected)}",
            errors,
        )


def check_decode_against_rtl(contract: dict, errors: list[str]) -> None:
    top = read_text(ROOT / "rtl/top/hello_soc_top.sv")
    decoded = {}
    for rtl_name, value in re.findall(
        r"assign\s+(\w+)_sel\s*=.*?mmio_addr\[31:12\]\s*==\s*20'h([0-9A-Fa-f_]+)",
        top,
    ):
        if rtl_name in REGION_RTL_NAMES:
            decoded[REGION_RTL_NAMES[rtl_name]] = h(value) << 12

    for name, region in regions_by_name(contract).items():
        expected = h(region["base"])
        actual = decoded.get(name)
        require(
            actual == expected,
            f"decode base for {name} is {fmt_hex(actual or 0)}, contract expects {fmt_hex(expected)}",
            errors,
        )

    require("mmio_addr[11:8] == 4'h0" in top, "RTL implemented-window decode changed", errors)
    unmapped = f"{h(contract['hello_chip']['unmapped_read_value']):08X}"
    rtl_unmapped_values = {
        value.replace("_", "").upper()
        for value in re.findall(r"32'h([0-9A-Fa-f_]+)", top)
    }
    require(unmapped in rtl_unmapped_values, "RTL unmapped read value does not match contract", errors)


def check_register_offsets_against_rtl(contract: dict, errors: list[str]) -> None:
    regions = regions_by_name(contract)
    for region_name, path in MODULE_BY_REGION.items():
        rtl = read_text(path)
        rtl_offsets = {
            int(index, 16) * 4
            for index in re.findall(r"6'h([0-9A-Fa-f]+):\s*rdata\s*=", rtl)
        }
        contract_offsets = set()
        for reg in regions[region_name]["registers"]:
            offset = h(reg["offset"])
            contract_offsets.add(offset)
            require(
                offset in rtl_offsets,
                f"{region_name} register {reg['name']} offset {fmt_hex(offset, 2)} is missing in {path.relative_to(ROOT)}",
                errors,
            )
        undocumented = sorted(rtl_offsets - contract_offsets)
        for offset in undocumented:
            errors.append(
                f"{region_name} RTL exposes readable offset {fmt_hex(offset, 2)} in "
                f"{path.relative_to(ROOT)} but {CONTRACT_PATH.relative_to(ROOT)} does not document it"
            )


def check_debug_contract(errors: list[str]) -> None:
    bridge = read_text(ROOT / "rtl/debug/hello_dbg_mmio_bridge.sv")
    require("DBG_LAUNCH" in read_text(ROOT / "arch/debug.md"), "arch/debug.md no longer names DBG_LAUNCH", errors)
    require("addr_q[{dbg_addr[2:0], 2'b00} +: 4]" in bridge, "debug address nibble load changed", errors)
    require("wdata_q[{dbg_addr[2:0], 2'b00} +: 4]" in bridge, "debug data nibble load changed", errors)
    require("rdata_q[{rsel_q, 2'b00} +: 4]" in bridge, "debug readback nibble select changed", errors)


def check_qemu_virt_separation(contract: dict, errors: list[str]) -> None:
    qemu = contract["qemu_virt"]
    qemu_script = read_text(ROOT / "scripts/run_qemu.sh")
    renode_script = read_text(ROOT / "scripts/run_renode.sh")
    qemu_readme = read_text(ROOT / "sim/qemu/README.md")
    renode_repl = read_text(ROOT / "sim/renode/openphone_hello.repl")

    require("-machine virt" in qemu_script, "scripts/run_qemu.sh must launch qemu-system-riscv64 -machine virt", errors)
    require("qemu-virt" in qemu_script, "scripts/run_qemu.sh must label the target as qemu-virt", errors)
    require("qemu-virt" in renode_script, "scripts/run_renode.sh must label the target as qemu-virt", errors)
    require("software reference only" in qemu_readme, "sim/qemu/README.md must mark QEMU as software reference only", errors)
    require("not the hello-chip hardware ABI" in qemu_readme, "sim/qemu/README.md must separate qemu-virt from hardware ABI", errors)
    require(f"0x{h(qemu['load_address']):08x}" in renode_repl.lower(), "Renode RAM does not cover qemu-virt load address", errors)
    require(f"0x{h(qemu['uart_base']):08x}" in renode_repl.lower(), "Renode UART base does not match qemu-virt contract", errors)


def check_contract(contract: dict) -> list[str]:
    errors: list[str] = []
    hello = contract.get("hello_chip", {})
    require(contract["contract"]["version"] == 1, "contract version must be 1 for current hello chip", errors)
    require(hello.get("has_cpu") is False, "hello chip contract must state has_cpu=false", errors)
    require(
        hello.get("bus_master") == "package_debug_nibble_bridge",
        "hello chip bus master must be the package debug nibble bridge",
        errors,
    )
    require(
        contract["qemu_virt"]["target_kind"] == "software_reference_only",
        "qemu_virt target must be marked software_reference_only",
        errors,
    )
    check_generated_header(contract, errors)
    check_bootrom_against_rtl(contract, errors)
    check_decode_against_rtl(contract, errors)
    check_register_offsets_against_rtl(contract, errors)
    check_debug_contract(errors)
    check_qemu_virt_separation(contract, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-generated-header", action="store_true")
    args = parser.parse_args()

    contract = load_contract()
    if args.print_generated_header:
        print(generate_header(contract), end="")
        return 0

    errors = check_contract(contract)
    if errors:
        print("Platform contract check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Platform contract check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
