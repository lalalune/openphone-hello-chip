#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / "board/kicad/hello-demo"
BOARD_DOC_DIR = ROOT / "docs/board/kicad/hello-demo"
REPORT_DIR = ROOT / "board/reports/fab"
MANIFEST = "board/kicad/hello-demo/artifact-manifest.yaml"

REQUIRED_PROJECT_GLOBS = {
    "project": ["*.kicad_pro"],
    "schematic": ["*.kicad_sch"],
    "pcb": ["*.kicad_pcb"],
}

REQUIRED_RELEASE_EVIDENCE = {
    "erc transcript": ["**/*erc*.txt", "**/*erc*.log", "**/*erc*.rpt"],
    "drc transcript": ["**/*drc*.txt", "**/*drc*.log", "**/*drc*.rpt"],
    "gerber output": ["**/*.gbr", "**/*.gbrjob"],
    "drill output": ["**/*.drl", "**/*.xln"],
    "bom output": ["**/*bom*.csv", "**/*bom*.tsv", "**/*bom*.xml"],
    "position output": ["**/*pos*.csv", "**/*position*.csv"],
}


def matches(base: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    if base.is_dir():
        for pattern in patterns:
            found.extend(path for path in base.glob(pattern) if path.is_file())
    return sorted(set(found))


def main() -> int:
    parser = ArgumentParser(description="Check KiCad board fabrication artifacts.")
    parser.add_argument("--release", action="store_true", help="require release-ready KiCad and fab evidence")
    args = parser.parse_args()

    failures: list[str] = []
    blockers: list[str] = []

    manifest_args = [sys.executable, "scripts/check_manufacturing_artifacts.py", "--manifest", MANIFEST]
    if args.release:
        manifest_args.append("--release")
    manifest_check = subprocess.run(manifest_args, cwd=ROOT, capture_output=True, text=True)
    if manifest_check.returncode != 0:
        failures.append(f"{MANIFEST} validation failed")
        if manifest_check.stdout:
            failures.extend(f"manifest: {line}" for line in manifest_check.stdout.rstrip().splitlines())
        if manifest_check.stderr:
            failures.extend(f"manifest stderr: {line}" for line in manifest_check.stderr.rstrip().splitlines())

    if not BOARD_DIR.is_dir():
        failures.append("missing board/kicad/hello-demo directory")
    else:
        notes = BOARD_DOC_DIR / "fab-notes.md"
        if not notes.is_file():
            failures.append("missing docs/board/kicad/hello-demo/fab-notes.md")
        for label, patterns in REQUIRED_PROJECT_GLOBS.items():
            if not matches(BOARD_DIR, patterns):
                blockers.append(f"missing KiCad {label} artifact under board/kicad/hello-demo")

    for label, patterns in REQUIRED_RELEASE_EVIDENCE.items():
        if not matches(REPORT_DIR, patterns) and not matches(BOARD_DIR, patterns):
            blockers.append(f"missing KiCad/fab release evidence: {label}")

    if failures:
        print("KiCad artifact check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    if blockers:
        print("KiCad release blockers:")
        for blocker in blockers:
            print(f"  - {blocker}")
        if args.release:
            return 1
        print("KiCad scaffold present; release evidence is still blocked.")
        return 0

    print("KiCad artifact check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
