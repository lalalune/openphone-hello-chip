#!/usr/bin/env python3
"""Check the generated Chipyard artifacts against the next boot-payload path.

This gate is intentionally narrower than a Linux boot claim. It verifies that
the generated DTS/artifacts are present enough to be handed to external
OpenSBI/U-Boot/Linux work, then reports the missing evidence that still blocks
any on-chip/RTL boot claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/chipyard/openphone_rocket"
GENERATED_SRC = OUT / "generated-src"
DTS = OUT / "openphone-hello.dts"
VERILOG = OUT / "openphone_rocket_ap.v"
SIMULATOR = OUT / "simulator"
GENERATED_MANIFEST = OUT / "OpenPhoneRocketConfig.manifest.json"
REPORT = ROOT / "build/reports/chipyard_payload_path.json"

REQUIRED_DTS_TOKENS = {
    "cpu": "cpu@0",
    "memory": "memory@80000000",
    "clint": "clint@2000000",
    "plic": "interrupt-controller@c000000",
    "serial": "serial@10020000",
    "chosen_stdout": "stdout-path",
}

EVIDENCE: dict[str, dict[str, Path | str]] = {
    "opensbi_boot_log": {
        "path": ROOT / "build/evidence/cpu_ap/openphone_hello_opensbi_boot.log",
        "next": "python3 scripts/capture_cpu_ap_evidence.py intake opensbi-boot --source /path/to/opensbi-serial.log --command '/exact/external/boot command'",
    },
    "u_boot_build_log": {
        "path": ROOT / "docs/evidence/linux/u_boot_openphone_build.log",
        "next": "OPENPHONE_UBOOT_CMD='/exact/external/u-boot build command' sw/u-boot/capture-u-boot-evidence.sh /path/to/u-boot build",
    },
    "u_boot_boot_chain_log": {
        "path": ROOT / "docs/evidence/linux/u_boot_opensbi_boot_chain.log",
        "next": "OPENPHONE_UBOOT_BOOT_CMD='/exact/external boot-chain command' sw/u-boot/capture-u-boot-evidence.sh /path/to/u-boot boot-chain",
    },
    "linux_boot_log": {
        "path": ROOT / "build/evidence/cpu_ap/openphone_hello_linux_boot.log",
        "next": "python3 scripts/capture_cpu_ap_evidence.py intake linux-boot --source /path/to/linux-serial.log --command '/exact/external Linux boot command'",
    },
    "linux_trap_irq_log": {
        "path": ROOT / "build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log",
        "next": "python3 scripts/capture_cpu_ap_evidence.py intake trap-timer-irq --source /path/to/trap-irq.log --command '/exact/external validation command'",
    },
    "linux_isa_mmu_log": {
        "path": ROOT / "build/evidence/cpu_ap/openphone_hello_isa_cache_mmu.log",
        "next": "python3 scripts/capture_cpu_ap_evidence.py intake isa-cache-mmu --source /path/to/isa-mmu.log --command '/exact/external validation command'",
    },
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def artifact_status(path: Path, *, min_bytes: int = 1) -> dict[str, Any]:
    status: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
    }
    if path.exists():
        status["kind"] = "directory" if path.is_dir() else "file"
        if path.is_file():
            status["bytes"] = path.stat().st_size
            status["ok"] = path.stat().st_size >= min_bytes
        else:
            files = [child for child in path.rglob("*") if child.is_file()]
            status["file_count"] = len(files)
            status["ok"] = bool(files)
    else:
        status["ok"] = False
    return status


def main() -> int:
    errors: list[str] = []
    blockers: list[dict[str, str]] = []

    artifacts = {
        "generated_src": artifact_status(GENERATED_SRC),
        "dts": artifact_status(DTS, min_bytes=512),
        "verilog": artifact_status(VERILOG, min_bytes=1024),
        "simulator": artifact_status(SIMULATOR),
        "generated_manifest": artifact_status(GENERATED_MANIFEST, min_bytes=512),
    }
    for name, artifact in artifacts.items():
        if not artifact.get("ok"):
            if name == "generated_manifest":
                blockers.append(
                    {
                        "name": "generated_manifest",
                        "detail": f"missing or invalid {rel(GENERATED_MANIFEST)}",
                        "next": "python3 scripts/generate_chipyard_openphone.py after firtool/RISCV environment is available, or regenerate/import with a complete external Chipyard flow",
                    }
                )
            else:
                errors.append(
                    f"generated artifact {name} is missing or invalid: {artifact['path']}"
                )

    dts_checks: dict[str, bool] = {}
    if DTS.is_file():
        text = DTS.read_text(errors="ignore")
        for name, token in REQUIRED_DTS_TOKENS.items():
            dts_checks[name] = token in text
            if token not in text:
                errors.append(f"generated DTS missing {name} token: {token}")
    else:
        for name in REQUIRED_DTS_TOKENS:
            dts_checks[name] = False

    evidence_status: dict[str, dict[str, Any]] = {}
    for name, spec in EVIDENCE.items():
        path_value = spec["path"]
        next_value = spec["next"]
        if not isinstance(path_value, Path) or not isinstance(next_value, str):
            errors.append(f"evidence spec {name} is invalid")
            continue
        path = path_value
        exists = path.is_file()
        evidence_status[name] = {
            "path": rel(path),
            "exists": exists,
            "next": next_value,
        }
        if not exists:
            blockers.append(
                {
                    "name": name,
                    "detail": f"missing {rel(path)}",
                    "next": next_value,
                }
            )

    if errors:
        status = "fail"
        code = 1
    elif blockers:
        status = "blocked"
        code = 2
    else:
        status = "pass"
        code = 0

    report = {
        "schema": "openphone.chipyard_payload_path.v1",
        "status": status,
        "claim_boundary": "generated_chipyard_artifacts_only_not_rtl_boot_claim",
        "summary": "Generated Chipyard artifacts may feed the next external OpenSBI/U-Boot/Linux payload path, but do not prove RTL boot.",
        "artifacts": artifacts,
        "dts_checks": dts_checks,
        "evidence": evidence_status,
        "blockers": blockers,
        "errors": errors,
        "next_smallest_step": "Complete generated import manifest, then capture OpenSBI handoff before U-Boot/Linux boot evidence.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if status == "fail":
        print("STATUS: FAIL chipyard.payload_path - generated artifacts are not usable")
        for error in errors:
            print(f"  - {error}")
    elif status == "blocked":
        print("STATUS: BLOCKED chipyard.payload_path - boot payload evidence is incomplete")
        for blocker in blockers:
            print(f"  - {blocker['detail']}")
            print(f"    next: {blocker['next']}")
    else:
        print("STATUS: PASS chipyard.payload_path - generated payload path evidence is complete")
    print(f"REPORT: {rel(REPORT)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
