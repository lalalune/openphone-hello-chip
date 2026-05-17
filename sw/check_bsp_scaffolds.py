#!/usr/bin/env python3
"""CLI audit for owned Android/Linux/Buildroot BSP scaffolds.

This script is intentionally repo-local and read-only. It does not replace the
top-level make targets; it gives BSP owners one command that classifies every
checked-in scaffold as either locally executable or externally blocked.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]


class CheckSpec(TypedDict):
    local: str
    expected: str
    blocker: str
    files: list[str]
    terms: list[str]


CHECKS: dict[str, CheckSpec] = {
    "linux": {
        "local": "make linux-bsp-check",
        "expected": "linux BSP check passed.",
        "blocker": "external Linux kernel checkout plus integration of drivers/misc/openphone-hello",
        "files": [
            "docs/sw/linux/README.md",
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
            "docs/sw/buildroot/README.md",
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
            "docs/sw/aosp-device/README.md",
            "docs/evidence/aosp-evidence.schema.json",
            "sw/aosp-device/import-aosp-device.sh",
            "sw/aosp-device/capture-aosp-evidence.sh",
            "sw/aosp-device/evidence_manifest.json",
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
            "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu_runtime.h",
            "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu_runtime.cc",
            "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu_probe_main.cc",
            "docs/sw/aosp-device/device/openphone/openphone_ai_soc/hal/README.md",
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "openphone_ai_soc",
            "hello_npu",
            "hwcomposer",
            "nnapi_acceleration=false",
            "unsupported",
            "vendorimage",
            "validation_command",
        ],
    },
    "boot": {
        "local": "make software-bsp-check",
        "expected": "buildroot BSP check passed.; linux BSP check passed.; aosp BSP check passed.",
        "blocker": "CPU-capable SoC integration with RAM, UART, timer, interrupt controller, OpenSBI handoff",
        "files": [
            "docs/sw/opensbi/README.md",
            "docs/sw/u-boot/README.md",
            "sw/opensbi/capture-opensbi-evidence.sh",
            "sw/u-boot/capture-u-boot-evidence.sh",
            "docs/evidence/software-bsp-capture.md",
            "docs/evidence/software-bsp-evidence.schema.json",
        ],
        "terms": [
            "sw/platform/hello_platform_contract.json",
            "dependency blocker",
            "expected output",
            "OpenSBI",
            "U-Boot",
            "validation_command",
        ],
    },
}


def read_joined(files: list[str]) -> str:
    return "\n".join(
        (ROOT / path).read_text(errors="ignore") for path in files if (ROOT / path).is_file()
    )


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

    if name == "aosp":
        errors.extend(check_aosp_hello_npu_host_probe())

    return errors


def check_aosp_hello_npu_host_probe() -> list[str]:
    errors: list[str] = []
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        return ["missing host C++ compiler for hello_npu fail-closed probe"]

    hal_dir = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/hal"
    sources = [
        hal_dir / "hello_npu_runtime.cc",
        hal_dir / "hello_npu_probe_main.cc",
    ]
    with tempfile.TemporaryDirectory(prefix="openphone-hello-npu-") as tmp:
        binary = Path(tmp) / "hello_npu_probe"
        missing_device = Path(tmp) / "missing-hello-npu"
        compile_cmd = [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(hal_dir),
            *[str(source) for source in sources],
            "-o",
            str(binary),
        ]
        compiled = subprocess.run(compile_cmd, text=True, capture_output=True)
        if compiled.returncode != 0:
            errors.append("hello_npu host probe failed to compile: " + compiled.stderr.strip())
            return errors

        probed = subprocess.run(
            [str(binary), "--device", str(missing_device)],
            text=True,
            capture_output=True,
        )
        if probed.returncode != 0:
            errors.append("hello_npu fail-closed probe returned nonzero: " + probed.stderr.strip())
            return errors
        output = probed.stdout
        required = [
            "hello_npu_status=unsupported",
            "device_node_present=false",
            "runtime_supported=false",
            "nnapi_acceleration=false",
            "claim_boundary=no_nnapi_acceleration_without_android_nnapi_hal_and_device_evidence",
        ]
        missing = [term for term in required if term not in output]
        if missing:
            errors.append("hello_npu fail-closed probe missing output terms: " + ", ".join(missing))

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
