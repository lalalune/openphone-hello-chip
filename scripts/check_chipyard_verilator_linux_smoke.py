#!/usr/bin/env python3
"""Fail-closed gate for the next Chipyard Verilator OpenSBI/Linux smoke step."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import stat
from pathlib import Path

import locate_chipyard_linux_payload

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
PROGRESS_MARKERS = (
    "SimDRAM loaded ELF entry=",
    "SimDRAM loading ELF ",
    "[UART] UART0 is here",
    "openphone-evidence: command=",
    "openphone-evidence: timeout_after_seconds=",
    "openphone-evidence: exit_code=",
)
CONTAINER_PATH_ENV = "CHIPYARD_ALLOW_CONTAINER_GENERATED_PATHS"
GENERATED_CONFIG_DIR = SIM_DIR / "generated-src/chipyard.harness.TestHarness.OpenPhoneRocketConfig"
GENERATED_DRIVER_MAKEFILE = (
    GENERATED_CONFIG_DIR / "chipyard.harness.TestHarness.OpenPhoneRocketConfig" / "VTestDriver.mk"
)
GENERATED_DRIVER_DIR = GENERATED_DRIVER_MAKEFILE.parent
GENERATED_FILELISTS = (
    GENERATED_CONFIG_DIR / "sim_files.common.f",
    GENERATED_CONFIG_DIR / "sim_files.f",
)
GENERATED_SIMULATOR = SIM_DIR / f"simulator-chipyard.harness-{CONFIG}"
STALE_ABSOLUTE_ROOTS = ("/work/", "/workspace/", "/__w/")
TRACE_LINE_RE = re.compile(
    r"^C(?P<hart>\d+):\s+(?P<cycle>\d+)\s+\[(?P<valid>[01])\]\s+pc=\[(?P<pc>[0-9a-fA-F]+)\]"
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def next_command(payload: str = f"${PAYLOAD_ENV}") -> str:
    return f"{PAYLOAD_ENV}={payload} scripts/run_chipyard_openphone_linux_smoke.sh"


def host_path_from_log(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    if path_text.startswith("/work/"):
        return ROOT / path_text.removeprefix("/work/")
    return Path(path_text)


def detect_stale_absolute_roots(
    text: str, host_root: Path, allow_container_paths: bool
) -> list[str]:
    if allow_container_paths:
        return []
    host_root_text = str(host_root)
    return sorted(
        {
            token
            for token in STALE_ABSOLUTE_ROOTS
            if token in text and not host_root_text.startswith(token.rstrip("/"))
        }
    )


def generated_path_blockers() -> list[str]:
    blockers: list[str] = []
    allow_container_paths = os.environ.get(CONTAINER_PATH_ENV) == "1"
    partial_generated = GENERATED_CONFIG_DIR.exists() and not GENERATED_DRIVER_MAKEFILE.is_file()
    for generated_filelist in GENERATED_FILELISTS:
        if generated_filelist.is_file():
            filelist_text = generated_filelist.read_text(encoding="utf-8", errors="replace")
            stale_roots = detect_stale_absolute_roots(filelist_text, ROOT, allow_container_paths)
            if stale_roots:
                blockers.append(
                    "generated Verilator filelist contains stale container/workspace "
                    f"absolute paths ({', '.join(stale_roots)}): {rel(generated_filelist)}; "
                    "regenerate the full generated-src config directory on this host or run "
                    "`CHIPYARD_LINUX_SMOKE_USE_DOCKER=1 scripts/run_chipyard_openphone_linux_smoke.sh` "
                    "inside the /work-mounted container path"
                )
    if GENERATED_DRIVER_MAKEFILE.is_file():
        makefile_text = GENERATED_DRIVER_MAKEFILE.read_text(encoding="utf-8", errors="replace")
        stale_roots = detect_stale_absolute_roots(makefile_text, ROOT, allow_container_paths)
        if stale_roots:
            blockers.append(
                "generated Verilator driver makefile contains stale container/workspace "
                f"absolute paths ({', '.join(stale_roots)}): {rel(GENERATED_DRIVER_MAKEFILE)}; "
                "regenerate the simulator on this host with "
                "`scripts/run_chipyard_openphone_verilator.sh run-binary` or run "
                "`CHIPYARD_LINUX_SMOKE_USE_DOCKER=1 scripts/run_chipyard_openphone_linux_smoke.sh` "
                "inside the /work-mounted container path"
            )
    elif (SIM_DIR / "generated-src").exists():
        blockers.append(
            "partial generated Verilator output is missing the driver makefile after generation: "
            f"{rel(GENERATED_DRIVER_MAKEFILE)}; remove the generated config directory and rerun "
            "`scripts/run_chipyard_openphone_linux_smoke.sh` so Chipyard regenerates the model"
        )
    if GENERATED_DRIVER_DIR.is_dir():
        zero_outputs = sorted(
            path
            for pattern in ("VTestDriver*.o", "VTestDriver__ALL.*")
            for path in GENERATED_DRIVER_DIR.glob(pattern)
            if path.is_file() and path.stat().st_size == 0
        )
        if zero_outputs:
            blockers.append(
                "partial generated Verilator output contains zero-byte model artifacts: "
                + ", ".join(rel(path) for path in zero_outputs[:5])
                + "; remove the generated config directory and rerun "
                "`scripts/run_chipyard_openphone_linux_smoke.sh`"
            )
    if partial_generated:
        blockers.append(
            "partial generated Verilator config directory exists without a complete driver model: "
            f"{rel(GENERATED_CONFIG_DIR)}"
        )
    return blockers


def remove_path(path: Path) -> None:
    def onerror(function, path_value, _exc_info):
        try:
            os.chmod(path_value, stat.S_IRWXU)
            function(path_value)
        except FileNotFoundError:
            pass

    if path.is_dir():
        shutil.rmtree(path, onerror=onerror)
    else:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def repair_stale_generated_paths() -> int:
    blockers = generated_path_blockers()
    repairable = [
        blocker
        for blocker in blockers
        if "stale container/workspace absolute paths" in blocker
        or "partial generated Verilator" in blocker
        or "zero-byte model artifacts" in blocker
    ]
    if not repairable:
        print("STATUS: PASS chipyard.verilator_generated_paths")
        print(f"  generated_driver_makefile: {rel(GENERATED_DRIVER_MAKEFILE)}")
        return 0

    print("STATUS: REPAIR chipyard.verilator_generated_paths")
    for blocker in repairable:
        print(f"  - {blocker}")
    print(f"  removing: {rel(GENERATED_CONFIG_DIR)}")
    remove_path(GENERATED_CONFIG_DIR)
    print(f"  removing: {rel(GENERATED_SIMULATOR)}")
    remove_path(GENERATED_SIMULATOR)
    print("  next: rerun the Chipyard make target so VTestDriver.mk is regenerated on this host")
    return 0


def parse_log_metadata() -> dict[str, object]:
    metadata: dict[str, object] = {
        "exists": LOG.is_file(),
        "exit_code": None,
        "payload": None,
        "binary_arg": None,
        "command": None,
        "timeout_after_seconds": None,
        "timeout_cycles": None,
        "run_target": None,
        "raw_transcript_closed": False,
        "lines_after_raw_transcript_end": 0,
        "fatal_errors": [],
        "simdram_entry": None,
        "simdram_load_range": None,
        "last_progress_marker": "",
    }
    if not LOG.is_file():
        return metadata

    last_progress = ""
    raw_transcript_closed = False
    lines_after_raw_transcript_end = 0
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw_transcript_closed and line.strip() and not line.startswith("openphone-evidence:"):
            lines_after_raw_transcript_end += 1
        if line.startswith("openphone-evidence: exit_code="):
            metadata["exit_code"] = line.split("=", 1)[1].strip()
        elif line.startswith("openphone-evidence: payload="):
            metadata["payload"] = line.split("=", 1)[1].strip()
        elif line.startswith("openphone-evidence: binary_arg="):
            metadata["binary_arg"] = line.split("=", 1)[1].strip()
        elif line.startswith("openphone-evidence: command="):
            metadata["command"] = line.split("=", 1)[1].strip()
            last_progress = line
        elif line.startswith("openphone-evidence: timeout_after_seconds="):
            metadata["timeout_after_seconds"] = line.split("=", 1)[1].strip()
            last_progress = line
        elif line.startswith("openphone-evidence: timeout_cycles="):
            metadata["timeout_cycles"] = line.split("=", 1)[1].strip()
        elif line.startswith("openphone-evidence: run_target="):
            metadata["run_target"] = line.split("=", 1)[1].strip()
        elif line.startswith("openphone-evidence: raw_transcript_end"):
            metadata["raw_transcript_closed"] = True
            raw_transcript_closed = True
        elif line.startswith("SimDRAM loading ELF "):
            marker = " into mem="
            if marker in line:
                metadata["simdram_load_range"] = line.rsplit(marker, 1)[1].strip()
            last_progress = line
        elif line.startswith("SimDRAM loaded ELF entry="):
            metadata["simdram_entry"] = line.split("=", 1)[1].strip()
            last_progress = line
        elif any(marker in line for marker in PROGRESS_MARKERS):
            last_progress = line
        if "fatal error:" in line:
            fatal_errors = metadata["fatal_errors"]
            if isinstance(fatal_errors, list):
                fatal_errors.append(line.strip())
    metadata["last_progress_marker"] = last_progress
    metadata["lines_after_raw_transcript_end"] = lines_after_raw_transcript_end
    return metadata


def output_stem_for_payload(payload: str | None) -> str:
    if not payload or payload == "none":
        return "none"
    return Path(payload).name


def parse_instruction_trace(payload: str | None) -> dict[str, object]:
    trace = (
        SIM_DIR
        / "output"
        / f"chipyard.harness.TestHarness.{CONFIG}"
        / f"{output_stem_for_payload(payload)}.out"
    )
    metadata: dict[str, object] = {
        "path": rel(trace),
        "exists": trace.is_file(),
        "retired_instruction_count": 0,
        "first_pc": None,
        "last_pc": None,
        "last_cycle": None,
        "entered_bootrom": False,
        "entered_payload": False,
        "bootrom_to_payload_handoff": False,
    }
    if not trace.is_file():
        return metadata

    first_pc: int | None = None
    last_pc: int | None = None
    last_cycle: int | None = None
    retired = 0
    entered_bootrom = False
    entered_payload = False
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TRACE_LINE_RE.match(line)
        if not match or match.group("valid") != "1":
            continue
        pc = int(match.group("pc"), 16)
        if first_pc is None:
            first_pc = pc
        last_pc = pc
        last_cycle = int(match.group("cycle"))
        retired += 1
        if 0x10000 <= pc < 0x20000:
            entered_bootrom = True
        if pc >= 0x80000000:
            entered_payload = True

    metadata.update(
        {
            "retired_instruction_count": retired,
            "first_pc": f"0x{first_pc:016x}" if first_pc is not None else None,
            "last_pc": f"0x{last_pc:016x}" if last_pc is not None else None,
            "last_cycle": last_cycle,
            "entered_bootrom": entered_bootrom,
            "entered_payload": entered_payload,
            "bootrom_to_payload_handoff": entered_bootrom and entered_payload,
        }
    )
    return metadata


def write_report(status: str, blockers: list[str], payload: str | None) -> None:
    allow_container_paths = os.environ.get(CONTAINER_PATH_ENV) == "1"
    log_metadata = parse_log_metadata()
    instruction_trace = parse_instruction_trace(payload)
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
        "log_metadata": log_metadata,
        "instruction_trace": instruction_trace,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "allow_container_generated_paths": allow_container_paths,
        "generated_driver_makefile": rel(GENERATED_DRIVER_MAKEFILE),
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repair-stale-generated",
        action="store_true",
        help=(
            "delete only stale generated Verilator driver outputs so the next "
            "Chipyard build regenerates host-correct absolute paths"
        ),
    )
    args = parser.parse_args()
    if args.repair_stale_generated:
        return repair_stale_generated_paths()

    blockers: list[str] = []
    log_metadata = parse_log_metadata()
    payload = os.environ.get(PAYLOAD_ENV)
    payload_source = "env"
    if not payload:
        logged_payload = log_metadata.get("payload")
        if isinstance(logged_payload, str):
            mapped_payload = host_path_from_log(logged_payload)
            if mapped_payload is not None:
                payload = str(mapped_payload)
                payload_source = "log"
    if not payload:
        for candidate in locate_chipyard_linux_payload.candidate_paths([], defaults=True):
            info, _error = locate_chipyard_linux_payload.read_elf_info(candidate)
            if info and info.runnable:
                payload = str(info.path)
                payload_source = "locator"
                break

    if not SIM_DIR.is_dir():
        blockers.append(f"missing Chipyard Verilator directory: {rel(SIM_DIR)}")

    blockers.extend(generated_path_blockers())

    for artifact in REQUIRED_GENERATED_ARTIFACTS:
        if not artifact.is_file():
            blockers.append(f"missing generated Verilog artifact: {rel(artifact)}")

    if not payload:
        blockers.append(
            f"{PAYLOAD_ENV} is unset, {rel(LOG)} does not record a replayable payload, "
            "and no FireMarshal OpenSBI/Linux ELF payload was found; run "
            "python3 scripts/locate_chipyard_linux_payload.py --require for build guidance"
        )
    elif not Path(payload).is_file():
        blockers.append(
            f"{PAYLOAD_ENV} {payload_source} payload does not point to a file: {payload}"
        )

    instruction_trace = parse_instruction_trace(payload)
    if not LOG.is_file():
        blockers.append(f"missing Verilator OpenSBI/Linux smoke log: {rel(LOG)}")
    else:
        text = LOG.read_text(encoding="utf-8", errors="replace")
        if "openphone-evidence: raw_transcript_begin" in text and not log_metadata.get(
            "raw_transcript_closed"
        ):
            blockers.append(
                f"{rel(LOG)} has raw_transcript_begin but lacks raw_transcript_end; "
                "the smoke attempt was interrupted before the wrapper recorded a complete result"
            )
        lines_after_end = log_metadata.get("lines_after_raw_transcript_end")
        if isinstance(lines_after_end, int) and lines_after_end:
            blockers.append(
                f"{rel(LOG)} contains {lines_after_end} non-empty line(s) after "
                "raw_transcript_end; timeout handling allowed simulator output to outlive "
                "the evidence wrapper"
            )
        fatal_errors = log_metadata.get("fatal_errors")
        if isinstance(fatal_errors, list):
            for fatal_error in fatal_errors:
                blockers.append(f"{rel(LOG)} records build fatal error: {fatal_error}")
        exit_code = log_metadata.get("exit_code")
        if exit_code and exit_code != "0":
            reason = f"{rel(LOG)} records simulator wrapper exit_code={exit_code}"
            timeout_after = log_metadata.get("timeout_after_seconds")
            if timeout_after:
                reason += f" after timeout_after_seconds={timeout_after}"
            blockers.append(reason)
        last_progress = log_metadata.get("last_progress_marker")
        if last_progress and not any(marker in text for marker in REQUIRED_LOG_MARKERS):
            blockers.append(f"last simulator progress before missing boot markers: {last_progress}")
        if instruction_trace.get("bootrom_to_payload_handoff") and not any(
            marker in text for marker in REQUIRED_LOG_MARKERS
        ):
            blockers.append(
                "instruction trace proves CPU forward progress through boot ROM "
                f"to payload: first_pc={instruction_trace.get('first_pc')} "
                f"last_pc={instruction_trace.get('last_pc')} "
                f"retired={instruction_trace.get('retired_instruction_count')} "
                f"trace={instruction_trace.get('path')}"
            )
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
