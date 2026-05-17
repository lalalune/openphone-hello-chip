#!/usr/bin/env python3
"""CLI audit for owned Android/Linux/Buildroot BSP scaffolds.

This script is intentionally repo-local and read-only. It does not replace the
top-level make targets; it gives BSP owners one command that classifies every
checked-in scaffold as either locally executable or externally blocked.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CHECKS = {
    "linux": {
        "local": "make linux-bsp-check",
        "expected": "linux BSP check passed.",
        "blocker": "external Linux kernel checkout plus integration of drivers/misc/openphone-hello",
        "files": [
            "sw/linux/README.md",
            "sw/linux/scripts/import-linux-bsp.sh",
            "sw/linux/dts/openphone-hello.dts",
            "sw/linux/drivers/hello/hello_platform_contract.h",
            "sw/linux/drivers/hello/Kconfig",
            "sw/linux/drivers/hello/Makefile",
            "sw/linux/drivers/hello/hello-npu.c",
            "sw/linux/drivers/hello/hello-dma.c",
            "sw/linux/tests/hello-mmio-smoke.c",
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "HELLO_NPU_BASE",
            "HELLO_DMA_BASE",
            "HELLO_DISPLAY_BASE",
            "openphone,hello-npu",
            "openphone,hello-dma",
            "openphone,hello-display",
        ],
    },
    "buildroot": {
        "local": "make buildroot-check",
        "expected": "buildroot BSP check passed.",
        "blocker": "external Buildroot checkout and external Linux kernel tarball/tree",
        "files": [
            "sw/buildroot/README.md",
            "sw/buildroot/external.desc",
            "sw/buildroot/Config.in",
            "sw/buildroot/external.mk",
            "sw/buildroot/scripts/import-buildroot-external.sh",
            "sw/buildroot/configs/openphone_hello_defconfig",
            "sw/buildroot/board/openphone/hello/linux.fragment",
            "sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke",
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "BR2_EXTERNAL_OPENPHONE_HELLO_PATH",
            "HELLO_NPU_BASE",
            "HELLO_DMA_BASE",
            "HELLO_DISPLAY_BASE",
        ],
    },
    "aosp": {
        "local": "make aosp-bsp-check",
        "expected": "aosp BSP check passed.",
        "blocker": "external AOSP checkout with riscv64/Cuttlefish host dependencies and HAL binaries",
        "files": [
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
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "openphone_ai_soc",
            "hello_npu",
            "hwcomposer",
            "vendorimage",
        ],
    },
    "boot": {
        "local": "make software-bsp-check",
        "expected": "buildroot BSP check passed.; linux BSP check passed.; aosp BSP check passed.",
        "blocker": "CPU-capable SoC integration with RAM, UART, timer, interrupt controller, OpenSBI handoff",
        "files": [
            "sw/opensbi/README.md",
            "sw/u-boot/README.md",
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "dependency blocker",
            "expected output",
        ],
    },
}


def read_joined(files: list[str]) -> str:
    return "\n".join((ROOT / path).read_text(errors="ignore") for path in files if (ROOT / path).is_file())


def check(name: str) -> list[str]:
    spec = CHECKS[name]
    errors: list[str] = []

    missing = [path for path in spec["files"] if not (ROOT / path).is_file()]
    if missing:
        errors.append("missing files: " + ", ".join(missing))
        return errors

    text = read_joined(spec["files"]).lower()
    missing_terms = [term for term in spec["terms"] if term.lower() not in text]
    if missing_terms:
        errors.append("missing scaffold terms: " + ", ".join(missing_terms))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=[*CHECKS.keys(), "all"], nargs="?", default="all")
    args = parser.parse_args()

    names = CHECKS.keys() if args.target == "all" else [args.target]
    failed = False

    for name in names:
        errors = check(name)
        spec = CHECKS[name]
        print(f"{name}: scaffold audit")
        print(f"  local command: {spec['local']}")
        print(f"  expected output: {spec['expected']}")
        print(f"  dependency blocker: {spec['blocker']}")
        if errors:
            failed = True
            for error in errors:
                print(f"  error: {error}")
        else:
            print("  status: clear")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
