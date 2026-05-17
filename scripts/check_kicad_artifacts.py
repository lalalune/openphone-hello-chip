#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KICAD_DIR = ROOT / "board/kicad/hello-demo"
FAB_REPORT_DIR = ROOT / "board/reports/fab"
COMMANDS_DOC = ROOT / "docs/board/kicad/hello-demo-commands.md"
MANIFEST = ROOT / "docs/board/kicad/hello-demo-artifact-manifest.yaml"
PINOUT = ROOT / "package/hello-demo-pinout.yaml"
PACKAGE_DOC = ROOT / "docs/package/hello-demo-package.md"

REQUIRED_KICAD_SOURCES = {
    "project": ["*.kicad_pro"],
    "schematic": ["*.kicad_sch"],
    "pcb": ["*.kicad_pcb"],
    "symbol_library": ["*.kicad_sym"],
    "footprint_modules": ["*.pretty/*.kicad_mod"],
}

REQUIRED_FAB_OUTPUTS = {
    "erc_transcript": ["erc*.txt", "erc*.log", "erc*.rpt"],
    "drc_transcript": ["drc*.txt", "drc*.log", "drc*.rpt"],
    "gerber_outputs": ["gerbers/*.gbr", "gerbers/*.gbrjob"],
    "drill_outputs": ["drill/*.drl", "drill/*.xln"],
    "bom_export": ["bom*.csv", "bom*.tsv", "bom*.xml"],
    "position_export": ["position*.csv", "positions*.csv", "pos*.csv"],
    "fab_drawing": ["fab-drawing*.pdf", "fab-drawing*.svg", "plot/*.pdf"],
    "command_transcript": ["command-transcript*.txt", "commands*.log"],
    "tool_versions": ["tool-versions*.txt", "tool_versions*.txt"],
}


def repo_rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{repo_rel(path)} must be a YAML mapping")
    return data


def matches(root: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(found))


def require_file(path: Path, label: str, failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"missing {label}: {repo_rel(path)}")


def validate_manifest_only(failures: list[str]) -> None:
    for path, label in (
        (KICAD_DIR / "fab-notes.md", "KiCad fabrication notes"),
        (COMMANDS_DOC, "KiCad command capture plan"),
        (MANIFEST, "KiCad artifact manifest"),
        (PINOUT, "package pinout"),
        (PACKAGE_DOC, "package contract"),
    ):
        require_file(path, label, failures)
    if failures:
        return

    manifest = load_yaml(MANIFEST)
    if manifest.get("status") != "release_blocked":
        failures.append("KiCad artifact manifest status must remain release_blocked")
    if manifest.get("kicad_project_dir") != "board/kicad/hello-demo":
        failures.append("KiCad artifact manifest must point at board/kicad/hello-demo")
    if manifest.get("fab_report_dir") != "board/reports/fab":
        failures.append("KiCad artifact manifest must point at board/reports/fab")
    if manifest.get("command_capture_doc") != "docs/board/kicad/hello-demo-commands.md":
        failures.append("KiCad artifact manifest must link the command capture doc")
    blocked_until = manifest.get("blocked_until")
    if not isinstance(blocked_until, list) or len(blocked_until) < 5:
        failures.append("KiCad artifact manifest must list concrete blocked_until prerequisites")
    sections = manifest.get("required_artifacts")
    expected_sections = {"sources", "fabrication_outputs", "provenance"}
    if not isinstance(sections, dict):
        failures.append("KiCad artifact manifest must list required_artifacts")
    else:
        missing = sorted(expected_sections - set(sections))
        if missing:
            failures.append(
                "KiCad artifact manifest missing required_artifacts sections: " + ", ".join(missing)
            )

    commands = COMMANDS_DOC.read_text()
    for phrase in (
        "kicad-cli sch erc",
        "kicad-cli pcb drc",
        "kicad-cli pcb export gerbers",
        "kicad-cli pcb export drill",
        "kicad-cli sch export bom",
        "kicad-cli pcb export pos",
    ):
        if phrase not in commands:
            failures.append(f"KiCad command capture doc missing command phrase: {phrase}")


def validate_release_artifacts(failures: list[str]) -> None:
    validate_manifest_only(failures)
    if failures:
        return

    pinout = load_yaml(PINOUT)
    package_name = str(pinout.get("package", "")).lower()
    notes = "\n".join(str(note).lower() for note in pinout.get("notes", []))
    if "placeholder" in package_name or "placeholder" in notes:
        failures.append(
            "package pinout is placeholder-only; do not generate fabrication KiCad artifacts from it"
        )

    package_text = PACKAGE_DOC.read_text().lower()
    if "not a foundry-approved package" in package_text or "placeholder" in package_text:
        failures.append("package contract is not vendor/foundry approved")

    for artifact, patterns in REQUIRED_KICAD_SOURCES.items():
        if not matches(KICAD_DIR, patterns):
            failures.append(f"missing KiCad {artifact} under {repo_rel(KICAD_DIR)}")

    for artifact, patterns in REQUIRED_FAB_OUTPUTS.items():
        if not matches(FAB_REPORT_DIR, patterns):
            failures.append(f"missing KiCad fab {artifact} under {repo_rel(FAB_REPORT_DIR)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed KiCad source and fabrication evidence gate."
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="check only blocker manifests and command-capture documentation",
    )
    args = parser.parse_args()

    failures: list[str] = []
    if args.manifest_only:
        validate_manifest_only(failures)
    else:
        validate_release_artifacts(failures)

    if failures:
        print("KiCad artifact check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    if args.manifest_only:
        print("KiCad artifact manifest gate ok")
    else:
        print("KiCad release artifacts ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
