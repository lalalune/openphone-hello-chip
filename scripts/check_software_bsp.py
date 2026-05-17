#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"

TARGETS = {
    "buildroot": {
        "readme": ROOT / "sw/buildroot/README.md",
        "required": [
            "sw/buildroot/external.desc",
            "sw/buildroot/Config.in",
            "sw/buildroot/external.mk",
            "sw/buildroot/scripts/import-buildroot-external.sh",
            "sw/buildroot/configs/openphone_hello_defconfig",
            "sw/buildroot/board/openphone/hello/linux.fragment",
            "sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke",
        ],
        "contract_terms": ["BR2_EXTERNAL_OPENPHONE_HELLO_PATH", "HELLO_NPU_BASE", "HELLO_DISPLAY_BASE", "HELLO_DMA_BASE"],
    },
    "linux": {
        "readme": ROOT / "sw/linux/README.md",
        "required": [
            "sw/linux/drivers/hello/Kconfig",
            "sw/linux/drivers/hello/Makefile",
            "sw/linux/scripts/import-linux-bsp.sh",
            "sw/linux/dts/openphone-hello.dts",
            "sw/linux/drivers/hello/hello-npu.c",
            "sw/linux/drivers/hello/hello-dma.c",
            "sw/linux/tests/hello-mmio-smoke.c",
        ],
        "contract_terms": ["CONFIG_OPENPHONE_HELLO_NPU", "CONFIG_OPENPHONE_HELLO_DMA", "openphone,hello-npu", "openphone,hello-dma", "openphone,hello-display"],
    },
    "aosp": {
        "readme": ROOT / "sw/aosp-device/README.md",
        "required": [
            "sw/aosp-device/import-aosp-device.sh",
            "sw/aosp-device/manifests/openphone-ai-soc-local.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
            "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
        ],
        "contract_terms": ["openphone_ai_soc", "hello_npu", "hwcomposer"],
    },
}


def check_contract(errors: list[str]) -> None:
    if not CONTRACT.is_file():
        errors.append("sw/platform/hello_platform_contract.json is missing")
        return
    data = json.loads(CONTRACT.read_text())
    if data.get("hello_chip", {}).get("has_cpu") is not False:
        errors.append("hello platform contract must keep hello_chip.has_cpu=false until a CPU exists")
    if data.get("qemu_virt", {}).get("target_kind") != "software_reference_only":
        errors.append("qemu_virt must be marked software_reference_only")


def check_aosp_product_glue(errors: list[str]) -> None:
    product = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk"
    board = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk"
    manifest = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml"
    text = product.read_text(errors="ignore") if product.is_file() else ""
    if "COMMON_LUNCH_CHOICES" not in text or "openphone_ai_soc-userdebug" not in text:
        errors.append("AOSP AndroidProducts.mk must expose openphone_ai_soc-userdebug lunch")
    board_text = board.read_text(errors="ignore") if board.is_file() else ""
    for term in ["TARGET_ARCH := riscv64", "BOARD_VENDOR_SEPOLICY_DIRS", "OPENPHONE_KERNEL_CONFIG_FRAGMENT", "OPENPHONE_DTS"]:
        if term not in board_text:
            errors.append(f"AOSP BoardConfig.mk missing {term}")
    if manifest.is_file():
        manifest_text = manifest.read_text(errors="ignore")
        for term in ["<manifest", "</manifest>", "<hal", "</hal>"]:
            if term not in manifest_text:
                errors.append(f"AOSP VINTF manifest missing XML marker {term}")


def check_target(name: str) -> list[str]:
    spec = TARGETS[name]
    errors: list[str] = []
    check_contract(errors)

    readme = spec["readme"]
    if not readme.is_file():
        errors.append(f"{readme.relative_to(ROOT)} is missing")
        return errors

    text = readme.read_text(errors="ignore")
    if "placeholder" in text.lower():
        errors.append(f"{readme.relative_to(ROOT)} still describes a placeholder-only target")
    if "sw/platform/hello_platform_contract.json" not in text:
        errors.append(f"{readme.relative_to(ROOT)} does not reference the central platform contract")

    missing = [path for path in spec["required"] if not (ROOT / path).exists()]
    if missing:
        errors.append(f"{name} BSP is not implemented; missing required artifacts: " + ", ".join(missing))

    present_text = "\n".join(
        path.read_text(errors="ignore")
        for path in (ROOT / spec_path for spec_path in spec["required"])
        if path.is_file()
    )
    if present_text:
        missing_terms = [term for term in spec["contract_terms"] if term not in present_text]
        if missing_terms:
            errors.append(f"{name} BSP artifacts do not expose expected contract terms: " + ", ".join(missing_terms))

    if name == "aosp":
        check_aosp_product_glue(errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=[*TARGETS.keys(), "all"])
    args = parser.parse_args()

    names = TARGETS.keys() if args.target == "all" else [args.target]
    failed = False
    for name in names:
        errors = check_target(name)
        scaffold = subprocess.run(
            [sys.executable, "sw/check_bsp_scaffolds.py", name],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if scaffold.stdout:
            print(scaffold.stdout, end="")
        if scaffold.stderr:
            print(scaffold.stderr, end="", file=sys.stderr)
        if scaffold.returncode:
            errors.append(f"{name} scaffold audit failed")
        if errors:
            failed = True
            print(f"{name} BSP check failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"{name} BSP check passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
