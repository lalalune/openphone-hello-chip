#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/aosp_linux_preflight.json"
CLAIM_BOUNDARY = (
    "host_preflight_only_not_aosp_build_boot_cuttlefish_or_hello_chip_hardware_evidence"
)


def command_version(command: str) -> str | None:
    path = shutil.which(command)
    if path is None:
        return None
    try:
        result = subprocess.run(
            [path, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return path
    first = result.stdout.splitlines()[0].strip() if result.stdout else ""
    return f"{path} ({first})" if first else path


def aosp_tool(aosp_dir: Path | None, *names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if aosp_dir is None:
        return None
    for name in names:
        candidate = aosp_dir / "out/host/linux-x86/bin" / name
        if candidate.exists():
            return str(candidate)
    return None


def group_output() -> str:
    try:
        return subprocess.check_output(["id", "-nG"], text=True).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def build_report(args: argparse.Namespace) -> tuple[int, dict]:
    blockers: list[str] = []
    warnings: list[str] = []
    host_os = os.uname().sysname
    host_arch = os.uname().machine
    aosp_dir_text = args.aosp_dir or os.environ.get("AOSP_DIR", "")
    aosp_dir = Path(aosp_dir_text).expanduser().resolve() if aosp_dir_text else None

    if host_os != "Linux":
        blockers.append("Linux host required for AOSP/Cuttlefish execution")

    if aosp_dir is None:
        blockers.append("AOSP_DIR is not set")
    else:
        if not (aosp_dir / "build/envsetup.sh").is_file():
            blockers.append(f"{aosp_dir}/build/envsetup.sh is missing")
        if not (aosp_dir / "device").is_dir():
            blockers.append(f"{aosp_dir}/device is missing")

    kvm = Path("/dev/kvm")
    if not kvm.exists():
        blockers.append("/dev/kvm is missing")
    elif not os.access(kvm, os.R_OK | os.W_OK):
        blockers.append("/dev/kvm is not readable and writable by this user")

    groups = group_output()
    group_set = set(groups.split())
    if host_os == "Linux" and not ({"kvm", "cvdnetwork"} & group_set):
        warnings.append("user is not in kvm or cvdnetwork group according to id -nG")

    required_tools = ["repo", "adb"]
    if args.require_qemu:
        required_tools.append("qemu-system-riscv64")
    missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    blockers.extend(f"{tool} not found on PATH" for tool in missing_tools)

    cuttlefish_launcher = aosp_tool(aosp_dir, "launch_cvd", "cvd")
    if cuttlefish_launcher is None:
        blockers.append(
            "Cuttlefish launcher not found; expected launch_cvd or cvd on PATH "
            "or under AOSP_DIR/out/host/linux-x86/bin"
        )

    report = {
        "schema": "openphone.aosp_linux_preflight.v1",
        "status": "blocked" if blockers else "pass",
        "claim_boundary": CLAIM_BOUNDARY,
        "aosp_dir": str(aosp_dir) if aosp_dir else "",
        "host": {
            "os": host_os,
            "arch": host_arch,
            "groups": groups,
            "dev_kvm": {
                "exists": kvm.exists(),
                "read_write": os.access(kvm, os.R_OK | os.W_OK) if kvm.exists() else False,
            },
        },
        "tools": {
            "repo": command_version("repo"),
            "adb": command_version("adb"),
            "qemu-system-riscv64": command_version("qemu-system-riscv64"),
            "cuttlefish_launcher": cuttlefish_launcher,
        },
        "blockers": blockers,
        "warnings": warnings,
        "next_step": (
            "Set AOSP_DIR to a Linux AOSP checkout with Cuttlefish/KVM available, "
            'then run sw/aosp-device/import-aosp-device.sh --check "$AOSP_DIR" '
            "and capture real evidence with sw/aosp-device/capture-aosp-evidence.sh."
        ),
        "evidence_policy": (
            "This preflight does not create docs/evidence/android logs and must not be "
            "used as AOSP build, boot, CTS, VTS, or hello-chip hardware evidence."
        ),
    }
    return (2 if blockers else 0), report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aosp-dir", help="External AOSP checkout; defaults to AOSP_DIR")
    parser.add_argument(
        "--require-qemu",
        action="store_true",
        help="Also require qemu-system-riscv64 for the optional QEMU smoke track.",
    )
    parser.add_argument("--json", action="store_true", help="Print only JSON report")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write {REPORT.relative_to(ROOT)} for commit-ready validation records.",
    )
    args = parser.parse_args()

    rc, report = build_report(args)
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif rc == 0:
        print("AOSP Linux preflight passed")
        print(f"claim_boundary={CLAIM_BOUNDARY}")
    else:
        print("AOSP Linux preflight BLOCKED:")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")
        for warning in report["warnings"]:
            print(f"  warning: {warning}")
        print(f"claim_boundary={CLAIM_BOUNDARY}")
        print(f"next_step={report['next_step']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
