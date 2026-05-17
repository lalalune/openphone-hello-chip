#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RELEASE_MANIFEST = ROOT / "docs/manufacturing/release-manifest.yaml"
GAP_MANIFEST = ROOT / "docs/manufacturing/real-world-verification-gaps.yaml"
WORK_ORDER = ROOT / "docs/manufacturing/physical-closure-work-order.yaml"
KICAD_MANIFEST = ROOT / "docs/board/kicad/hello-demo-artifact-manifest.yaml"

REQUIRED_EVIDENCE_PATHS = {
    "board_stackup": ROOT / "docs/manufacturing/evidence/board",
    "board_si": ROOT / "board/reports/si",
    "board_pi": ROOT / "board/reports/pi",
    "fab_reports": ROOT / "board/reports/fab",
    "package_evidence": ROOT / "docs/manufacturing/evidence/package",
    "dfm_evidence": ROOT / "docs/manufacturing/evidence/dfm",
    "lab_evidence": ROOT / "docs/manufacturing/evidence/lab",
}


def repo_rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{repo_rel(path)} must be a YAML mapping")
    return data


def require_file(path: Path, label: str, failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"missing {label}: {repo_rel(path)}")


def validate_manifest_only(failures: list[str]) -> None:
    for path, label in (
        (RELEASE_MANIFEST, "manufacturing release manifest"),
        (GAP_MANIFEST, "real-world gap manifest"),
        (WORK_ORDER, "physical closure work order"),
        (KICAD_MANIFEST, "KiCad artifact manifest"),
    ):
        require_file(path, label, failures)
    if failures:
        return

    release = load_yaml(RELEASE_MANIFEST)
    gaps = load_yaml(GAP_MANIFEST)
    work_order = load_yaml(WORK_ORDER)
    kicad = load_yaml(KICAD_MANIFEST)

    board_gate = release.get("blocked_gates", {}).get("board_fabrication_release")
    if not isinstance(board_gate, dict) or board_gate.get("blocked") is not True:
        failures.append("manufacturing board_fabrication_release gate must remain blocked")
    if (
        board_gate
        and board_gate.get("evidence_manifest") != "docs/manufacturing/release-manifest.yaml"
    ):
        failures.append(
            "manufacturing board_fabrication_release gate must point at release manifest"
        )

    if gaps.get("status") != "release_blocked":
        failures.append("real-world gap manifest must remain release_blocked")
    if work_order.get("status") != "release_blocked":
        failures.append("physical closure work order must remain release_blocked")
    if kicad.get("status") != "release_blocked":
        failures.append("KiCad artifact manifest must remain release_blocked")

    expected_gap_ids = {
        "board_stackup_and_return_paths",
        "board_signal_integrity_report",
        "power_integrity_report",
        "board_current_limit_plan",
        "board_footprint_release",
        "kicad_project_release",
        "footprint_source_checksum",
        "assembly_dfm_review",
        "first_article_smoke_limits",
    }
    gap_ids = {
        gap.get("id")
        for gap in gaps.get("gaps", [])
        if isinstance(gap, dict) and gap.get("release_gate") == "board_fabrication_release"
    }
    missing = sorted(expected_gap_ids - gap_ids)
    if missing:
        failures.append("board fabrication gap manifest missing ids: " + ", ".join(missing))

    item_ids = {
        item.get("id")
        for item in work_order.get("items", [])
        if isinstance(item, dict) and item.get("gate") == "board_fabrication_release"
    }
    missing_items = sorted(expected_gap_ids - item_ids)
    if missing_items:
        failures.append(
            "physical closure work order missing board fabrication ids: " + ", ".join(missing_items)
        )


def validate_release_artifacts(failures: list[str]) -> None:
    validate_manifest_only(failures)
    if failures:
        return

    kicad_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_kicad_artifacts.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if kicad_check.returncode != 0:
        failures.append("KiCad source/fab evidence gate is blocked")
        for line in (kicad_check.stdout + kicad_check.stderr).splitlines():
            if line.strip().startswith("- "):
                failures.append("KiCad: " + line.strip()[2:])

    for label, path in REQUIRED_EVIDENCE_PATHS.items():
        if not path.exists():
            failures.append(
                f"missing manufacturing evidence directory for {label}: {repo_rel(path)}"
            )
            continue
        if path.is_dir() and not any(child.is_file() for child in path.rglob("*")):
            failures.append(
                f"manufacturing evidence directory is empty for {label}: {repo_rel(path)}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed board manufacturing evidence gate.")
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="check only blocker manifests and work-order wiring",
    )
    args = parser.parse_args()

    failures: list[str] = []
    if args.manifest_only:
        validate_manifest_only(failures)
    else:
        validate_release_artifacts(failures)

    if failures:
        print("Manufacturing artifact check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    if args.manifest_only:
        print("manufacturing artifact manifest gate ok")
    else:
        print("manufacturing release artifacts ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
