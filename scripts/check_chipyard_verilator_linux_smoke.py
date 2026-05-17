#!/usr/bin/env python3
"""Fail-closed gate for the next Chipyard Verilator OpenSBI/Linux smoke step."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / "external/chipyard"
SIM_DIR = CHECKOUT / "sims/verilator"
OUT_DIR = ROOT / "build/chipyard/openphone_rocket"
REPORT = OUT_DIR / "verilator-linux-smoke.json"
LOG = OUT_DIR / "verilator-linux-smoke.log"
CONFIG = "OpenPhoneRocketConfig"
CONFIG_PACKAGE = "openphone"
PAYLOAD_ENV = "CHIPYARD_LINUX_BINARY"

REQUIRED_GENERATED_ARTIFACTS = (
    OUT_DIR / "openphone_rocket_ap.v",
    OUT_DIR / "generated-src/chipyard.harness.TestHarness.OpenPhoneRocketConfig.fir",
    OUT_DIR / "generated-src/chipyard.harness.TestHarness.OpenPhoneRocketConfig.dts",
    OUT_DIR / "OpenPhoneRocketConfig.manifest.json",
)
REQUIRED_LOG_MARKERS = ("OpenSBI", "Linux version")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def next_command(payload: str = f"${PAYLOAD_ENV}") -> str:
    return (
        "cd external/chipyard/sims/verilator && "
        "source ../../env.sh && "
        f"make CONFIG={CONFIG} CONFIG_PACKAGE={CONFIG_PACKAGE} "
        f"BINARY={payload} LOADMEM=1 run-binary"
    )


def write_report(status: str, blockers: list[str], payload: str | None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "openphone.chipyard_verilator_linux_smoke.v1",
        "status": status,
        "simulator_path": "external/chipyard/sims/verilator",
        "config": CONFIG,
        "config_package": CONFIG_PACKAGE,
        "payload_env": PAYLOAD_ENV,
        "payload": payload or "",
        "log": rel(LOG),
        "required_log_markers": list(REQUIRED_LOG_MARKERS),
        "next_command": next_command(),
        "blockers": blockers,
        "claim_boundary": (
            "This gate only passes after a real Chipyard Verilator run-binary log "
            "contains OpenSBI and Linux markers from the generated OpenPhoneRocketConfig. "
            "It does not create or substitute boot evidence."
        ),
    }
    tmp = REPORT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(REPORT)


def main() -> int:
    blockers: list[str] = []
    payload = os.environ.get(PAYLOAD_ENV)

    if not SIM_DIR.is_dir():
        blockers.append(f"missing Chipyard Verilator directory: {rel(SIM_DIR)}")

    for artifact in REQUIRED_GENERATED_ARTIFACTS:
        if not artifact.is_file():
            blockers.append(f"missing generated Verilog artifact: {rel(artifact)}")

    if not payload:
        blockers.append(
            f"{PAYLOAD_ENV} is unset; provide a real OpenSBI/Linux ELF payload before run-binary"
        )
    elif not Path(payload).is_file():
        blockers.append(f"{PAYLOAD_ENV} does not point to a file: {payload}")

    if not LOG.is_file():
        blockers.append(f"missing Verilator OpenSBI/Linux smoke log: {rel(LOG)}")
    else:
        text = LOG.read_text(encoding="utf-8", errors="replace")
        for marker in REQUIRED_LOG_MARKERS:
            if marker not in text:
                blockers.append(f"{rel(LOG)} lacks required marker: {marker}")

    if blockers:
        write_report("blocked", blockers, payload)
        print("STATUS: BLOCKED chipyard.verilator_linux_smoke")
        print(f"  simulator_path: {rel(SIM_DIR)}")
        print(f"  next_command: {next_command()}")
        for blocker in blockers:
            print(f"  - {blocker}")
        return 2

    write_report("pass", [], payload)
    print("STATUS: PASS chipyard.verilator_linux_smoke")
    print(f"  simulator_path: {rel(SIM_DIR)}")
    print(f"  log: {rel(LOG)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
