#!/usr/bin/env python3
"""Check the target-side hello NPU Linux ML smoke wiring.

This is a source-level gate only. It must stay fail-closed until the checked-in
Linux driver UAPI, Buildroot smoke program, DTS compatible string, and evidence
manifest agree on the same target-side ABI and a real generated-AP transcript is
captured.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/hello_npu_linux_smoke_source.json"
SMOKE = ROOT / "sw/buildroot/package/hello-npu-ml-smoke/src/hello-npu-ml-smoke.c"
PACKAGE_CONFIG = ROOT / "sw/buildroot/package/hello-npu-ml-smoke/Config.in"
DRIVER = ROOT / "sw/linux/drivers/hello/hello-npu.c"
UAPI = ROOT / "sw/linux/drivers/hello/hello-npu-uapi.h"
DTS = ROOT / "sw/linux/dts/openphone-hello.dts"
BUILDROOT_CONFIG = ROOT / "sw/buildroot/Config.in"
BUILDROOT_DEFCONFIG = ROOT / "sw/buildroot/configs/openphone_hello_defconfig"
LINUX_EVIDENCE = ROOT / "docs/evidence/linux/openphone_hello_npu_ml_smoke.log"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def macro(text: str, name: str) -> str:
    match = re.search(rf"(?m)^#define\s+{re.escape(name)}\s+(.+)$", text)
    return match.group(1).strip() if match else ""


def require(problems: list[str], condition: bool, message: str) -> None:
    if not condition:
        problems.append(message)


def build_report() -> dict[str, Any]:
    smoke = read(SMOKE)
    driver = read(DRIVER)
    uapi = read(UAPI)
    dts = read(DTS)
    buildroot_config = read(BUILDROOT_CONFIG)
    package_config = read(PACKAGE_CONFIG)
    buildroot_defconfig = read(BUILDROOT_DEFCONFIG)
    problems: list[str] = []
    blockers: list[str] = []

    for path in (SMOKE, PACKAGE_CONFIG, DRIVER, UAPI, DTS, BUILDROOT_CONFIG, BUILDROOT_DEFCONFIG):
        require(problems, path.is_file(), f"missing required source: {rel(path)}")

    require(problems, "hello-npu-ml-smoke" in smoke, "smoke source lacks command identity")
    require(problems, "GEMM_S8" in smoke, "smoke source lacks GEMM_S8 workload marker")
    require(problems, "input_sha256" in smoke, "smoke source lacks input hash marker")
    require(problems, "output_sha256" in smoke, "smoke source lacks output hash marker")
    require(problems, "PASS" in smoke, "smoke source lacks PASS marker")
    require(
        problems,
        "CPU-only" in smoke or "cpu-only" in smoke.lower(),
        "smoke source must explicitly reject CPU-only fallback",
    )
    require(problems, "hello-npu" in driver, "driver source lacks hello-npu device name")
    require(problems, "openphone,hello-npu" in dts, "DTS lacks openphone,hello-npu compatible")
    require(
        problems,
        "package/hello-npu-ml-smoke/Config.in" in buildroot_config
        and "BR2_PACKAGE_HELLO_NPU_ML_SMOKE" in package_config,
        "Buildroot package is not sourced from Config.in or its package Config.in lacks the symbol",
    )
    require(
        problems,
        "BR2_PACKAGE_HELLO_NPU_ML_SMOKE=y" in buildroot_defconfig,
        "Buildroot defconfig does not enable hello-npu-ml-smoke",
    )

    smoke_magic = macro(smoke, "OPENPHONE_HELLO_NPU_IOC_MAGIC") or macro(
        smoke, "HELLO_NPU_IOC_MAGIC"
    )
    uapi_magic = macro(uapi, "HELLO_NPU_IOC_MAGIC")
    if smoke_magic and uapi_magic and smoke_magic != uapi_magic:
        problems.append(f"smoke ioctl magic {smoke_magic} does not match UAPI {uapi_magic}")
    elif not smoke_magic:
        problems.append("smoke source does not define or include the hello NPU ioctl magic")
    elif not uapi_magic:
        problems.append("UAPI header does not define HELLO_NPU_IOC_MAGIC")

    if "mmap(" in smoke and ".mmap" not in driver:
        problems.append(
            "smoke uses mmap but checked-in driver file_operations has no mmap implementation"
        )
    if "HELLO_NPU_IOC_RUN_GEMM_S8" in uapi and "HELLO_NPU_IOC_RUN_GEMM_S8" not in smoke:
        problems.append("smoke does not use the checked-in RUN_GEMM_S8 UAPI")

    if not LINUX_EVIDENCE.is_file():
        blockers.append(f"missing target transcript: {rel(LINUX_EVIDENCE)}")
    else:
        text = read(LINUX_EVIDENCE)
        for marker in (
            "openphone-evidence: target=linux artifact=hello_npu_ml_smoke",
            "hello-npu-ml-smoke: PASS",
            "workload=gemm_s8",
            "openphone-evidence: status=PASS",
        ):
            if marker not in text:
                problems.append(f"{rel(LINUX_EVIDENCE)} missing marker: {marker}")

    return {
        "schema": "openphone.hello_npu_linux_smoke_source.v1",
        "status": "fail" if problems else ("blocked" if blockers else "pass"),
        "claim_boundary": "source wiring and external transcript gate; not Linux runtime proof by itself",
        "sources": {
            "smoke": rel(SMOKE),
            "driver": rel(DRIVER),
            "uapi": rel(UAPI),
            "dts": rel(DTS),
            "buildroot_config": rel(BUILDROOT_CONFIG),
            "package_config": rel(PACKAGE_CONFIG),
            "buildroot_defconfig": rel(BUILDROOT_DEFCONFIG),
        },
        "evidence": rel(LINUX_EVIDENCE),
        "problems": problems,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"STATUS: {report['status'].upper()} hello_npu.linux_smoke_source")
        print(f"  report: {rel(REPORT)}")
        for problem in report["problems"]:
            print(f"  - {problem}")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")

    if report["status"] == "fail":
        return 1
    if report["status"] == "blocked" and args.require_pass:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
