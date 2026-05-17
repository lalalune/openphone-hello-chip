#!/usr/bin/env python3
"""AOSP BSP evidence asserter for openphone_ai_soc.

This script is the local gate for the AOSP device tree. It asserts that
the evidence files listed in docs/android/bsp-critical-gap-audit-2026-05-17.md
are present on disk. If any are missing, it prints BLOCKED with the
specific missing files and a human reason, and exits non-zero.

It does NOT inspect log contents, run AOSP builds, or talk to Cuttlefish.
A real PASS requires those logs to be checked in by a human after running
the build/boot on an external AOSP tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve repo root from this file's location:
#   <repo>/sw/aosp-device/scripts/check_aosp_bsp.py
ROOT = Path(__file__).resolve().parents[3]

# Required AOSP scaffold sources. Must all be present in this repo.
SCAFFOLD_FILES = [
    "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
    "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
    "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
    "sw/aosp-device/device/openphone/openphone_ai_soc/fstab.openphone",
    "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
    "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/hello_npu.te",
    "sw/aosp-device/device/openphone/openphone_ai_soc/kernel/openphone_ai_soc.fragment",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu/Android.bp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu/HelloNpu.cpp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu/HelloNpu.h",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu/service.cpp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu/IHelloNpu.hal",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hwcomposer/Android.bp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hwcomposer/hwcomposer.cpp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/hal/hwcomposer/service.cpp",
    "sw/aosp-device/device/openphone/openphone_ai_soc/README.md",
]

# Evidence files required by docs/android/bsp-critical-gap-audit-2026-05-17.md.
# Absent => BLOCKED with the named reason.
EVIDENCE_FILES = {
    "external AOSP lunch transcript": "docs/evidence/android/openphone_ai_soc_lunch.log",
    "external AOSP vendorimage build log": "docs/evidence/android/openphone_ai_soc_vendorimage.log",
    "external AOSP check_vintf log": "docs/evidence/android/openphone_ai_soc_checkvintf.log",
    "Cuttlefish riscv64 boot transcript": "docs/evidence/android/cuttlefish_riscv64_boot.log",
}


def main() -> int:
    failed = False

    # 1. Source scaffold presence.
    missing_sources = [p for p in SCAFFOLD_FILES if not (ROOT / p).is_file()]
    if missing_sources:
        failed = True
        print("aosp BSP BLOCKED: missing scaffold sources:")
        for p in missing_sources:
            print(f"  - {p}")
    else:
        print("aosp BSP sources: present (scaffold-only, not boot evidence)")

    # 2. Evidence presence (always BLOCKED in v0).
    missing_evidence = [
        (reason, path)
        for reason, path in EVIDENCE_FILES.items()
        if not (ROOT / path).is_file()
    ]
    if missing_evidence:
        failed = True
        print("aosp BSP BLOCKED: missing evidence:")
        for reason, path in missing_evidence:
            print(f"  - {path} ({reason})")
    else:
        print("aosp BSP evidence: all required logs present")

    if failed:
        print(
            "aosp BSP status: BLOCKED. "
            "Dependency blocker: external AOSP checkout with riscv64/Cuttlefish "
            "host dependencies and HAL binaries; "
            "host_checkable_manifest_only_not_boot_evidence."
        )
        return 1

    print("aosp BSP check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
