#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import Path

import yaml

PLACEHOLDERS = {None, "", "unassigned", "missing", "todo", "tbd", "none"}
VECTOR_PIN_RE = re.compile(r"^(DBG_ADDR|DBG_WDATA|DBG_RDATA|GPIO)(\d+)$")
LOCATE_RE = re.compile(r'^\s*LOCATE\s+COMP\s+"([^"]+)"\s+SITE\s+"([^"]+)"\s*;', re.I)
RELEASE_MANIFEST_SCHEMA = "openphone.fpga_release_manifest.v1"
REQUIRED_RELEASE_EVIDENCE = {
    "exact_board_revision",
    "final_pin_constraints",
    "nextpnr_timing",
    "ecppack_bitstream",
    "tool_versions",
}
FORBIDDEN_RELEASE_TEXT_MARKERS = (
    "template_not_release_evidence",
    "non_release_placeholder",
    "release use: `prohibited`",
    "release_use: prohibited",
    "placeholder-only",
    "skeleton lpf",
    "dummy bitstream",
    "fake bitstream",
    "not release evidence",
)


def is_placeholder(value: object) -> bool:
    return str(value).strip().lower() in PLACEHOLDERS


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a YAML mapping")
    return data


def required_physical_signals(root: Path, cfg: dict) -> set[str]:
    logical = {
        cfg["clock"]["port"],
        cfg["reset"]["port"],
        *cfg["debug_bridge"]["required_ports"],
        cfg["external_outputs"]["gpio_port"],
        *cfg["external_outputs"]["irq_ports"],
        *cfg.get("reserved_inputs", []),
        *cfg.get("reserved_outputs", []),
    }

    pinout = load_yaml(root / "package/hello-demo-pinout.yaml")
    signals: set[str] = set()
    for pin in pinout.get("pins", []):
        name = pin.get("name")
        if not isinstance(name, str) or name.startswith(("VDD", "VSS", "NC")):
            continue
        vector = VECTOR_PIN_RE.match(name)
        logical_name = vector.group(1) if vector else name
        if logical_name in logical:
            signals.add(name)
    return signals


def parse_locates(path: Path) -> dict[str, str]:
    locates: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = LOCATE_RE.match(line)
        if match:
            locates[match.group(1)] = match.group(2)
    return locates


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contains_forbidden_release_marker(path: Path) -> list[str]:
    text = path.read_text(errors="ignore").lower()
    return [marker for marker in FORBIDDEN_RELEASE_TEXT_MARKERS if marker in text]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "board/fpga/hello_demo_fpga.yaml"
    cfg = load_yaml(cfg_path)
    blockers: list[str] = []

    if cfg.get("status") != "release_ready":
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: status must be release_ready after real board, pin, timing, and bitstream evidence is archived"
        )

    board = cfg.get("board", {})
    for field in ["exact_revision", "exact_revision_evidence", "ecp5_device", "ecp5_package"]:
        if is_placeholder(board.get(field)):
            blockers.append(f"board/fpga/hello_demo_fpga.yaml: board.{field} is unassigned")

    constraints = cfg.get("constraints", {})
    if constraints.get("bitstream_release_blocked_until_pins_assigned") is True:
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: constraints.bitstream_release_blocked_until_pins_assigned is still true"
        )

    final_lpf_value = constraints.get("final_lpf")
    skeleton_lpf_value = constraints.get("skeleton_lpf")
    final_lpf = root / str(final_lpf_value)
    if is_placeholder(final_lpf_value):
        blockers.append("board/fpga/hello_demo_fpga.yaml: constraints.final_lpf is unassigned")
    elif final_lpf_value == skeleton_lpf_value:
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: constraints.final_lpf must not point at the skeleton LPF"
        )
    elif not final_lpf.is_file():
        blockers.append(f"missing final FPGA LPF: {final_lpf_value}")
    else:
        required = required_physical_signals(root, cfg)
        locates = parse_locates(final_lpf)
        missing = sorted(required - set(locates))
        if missing:
            blockers.append(
                f"{final_lpf_value}: missing LOCATE COMP assignments for {len(missing)} required physical signals: "
                + ", ".join(missing)
            )
        duplicate_sites = sorted(
            site for site in set(locates.values()) if list(locates.values()).count(site) > 1
        )
        if duplicate_sites:
            blockers.append(
                f"{final_lpf_value}: duplicate FPGA package SITE assignments: "
                + ", ".join(duplicate_sites)
            )
        expected_count = constraints.get("required_locate_assignments")
        if expected_count is not None and len(locates) < int(expected_count):
            blockers.append(
                f"{final_lpf_value}: has {len(locates)} LOCATE COMP assignments, expected at least {expected_count}"
            )
        clock_port = cfg["clock"]["port"]
        clock_hz = int(cfg["clock"]["nominal_frequency_hz"])
        clock_mhz = clock_hz // 1_000_000
        lpf_text = final_lpf.read_text()
        if f'FREQUENCY PORT "{clock_port}" {clock_mhz} MHz' not in lpf_text:
            blockers.append(
                f'{final_lpf_value}: missing clock constraint FREQUENCY PORT "{clock_port}" {clock_mhz} MHz'
            )

    manifest_value = cfg.get("release_evidence", {}).get("manifest")
    if is_placeholder(manifest_value) or not (root / str(manifest_value)).is_file():
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: release_evidence.manifest must point to an archived manifest"
        )
    else:
        manifest = load_yaml(root / str(manifest_value))
        if manifest.get("schema") != RELEASE_MANIFEST_SCHEMA:
            blockers.append(f"{manifest_value}: schema must be {RELEASE_MANIFEST_SCHEMA}")
        if manifest.get("status") != "release_ready":
            blockers.append(
                f"{manifest_value}: status is {manifest.get('status')}, not release_ready"
            )
        required_evidence = manifest.get("required_evidence")
        if not isinstance(required_evidence, dict):
            blockers.append(f"{manifest_value}: required_evidence must be a mapping")
        else:
            missing_evidence = sorted(REQUIRED_RELEASE_EVIDENCE - set(required_evidence))
            if missing_evidence:
                blockers.append(
                    f"{manifest_value}: missing required evidence entries: "
                    + ", ".join(missing_evidence)
                )
            for name, spec in required_evidence.items():
                if not isinstance(spec, dict):
                    blockers.append(f"{manifest_value}: required_evidence.{name} must be a mapping")
                    continue
                if spec.get("status") not in {"missing", "complete"}:
                    blockers.append(
                        f"{manifest_value}: required_evidence.{name}.status must be missing or complete"
                    )
                if not isinstance(spec.get("required_action"), str) or not spec["required_action"]:
                    blockers.append(
                        f"{manifest_value}: required_evidence.{name}.required_action is required"
                    )

    release = cfg.get("release_evidence", {})
    for tool in ["nextpnr-ecp5", "ecppack"]:
        if shutil.which(tool) is None:
            blockers.append(f"required FPGA release tool is not on PATH: {tool}")

    for field in ["timing_report", "timing_summary", "archived_tool_versions"]:
        value = release.get(field)
        if is_placeholder(value):
            blockers.append(
                f"board/fpga/hello_demo_fpga.yaml: release_evidence.{field} is unassigned"
            )
        elif not (root / str(value)).is_file():
            blockers.append(f"missing FPGA release evidence file: {value}")
        else:
            markers = contains_forbidden_release_marker(root / str(value))
            if markers:
                blockers.append(f"{value}: contains non-release marker(s): " + ", ".join(markers))

    bitstream_value = release.get("bitstream_path")
    bitstream_sha = release.get("bitstream_sha256")
    if is_placeholder(bitstream_value):
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: release_evidence.bitstream_path is unassigned"
        )
    elif not (root / str(bitstream_value)).is_file():
        blockers.append(f"missing FPGA bitstream file: {bitstream_value}")
    elif markers := contains_forbidden_release_marker(root / str(bitstream_value)):
        blockers.append(f"{bitstream_value}: contains non-release marker(s): " + ", ".join(markers))
    elif is_placeholder(bitstream_sha):
        blockers.append(
            "board/fpga/hello_demo_fpga.yaml: release_evidence.bitstream_sha256 is unassigned"
        )
    else:
        actual = file_sha256(root / str(bitstream_value))
        if actual.lower() != str(bitstream_sha).lower():
            blockers.append(
                f"{bitstream_value}: sha256 mismatch, expected {bitstream_sha}, got {actual}"
            )

    if blockers:
        print("FPGA release preflight blocked:")
        for blocker in blockers:
            print(f"  - {blocker}")
        return 1

    print("FPGA release preflight ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
