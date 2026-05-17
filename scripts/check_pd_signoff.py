#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import re
import sys

import yaml


REQUIRED_ARTIFACTS = {
    "gds": ".gds",
    "def": ".def",
    "gate_netlist": ".v",
    "sdc": ".sdc",
    "drc_report": ".rpt",
    "lvs_report": ".rpt",
    "antenna_report": ".rpt",
    "sta_report": ".rpt",
}


def as_list(value: object) -> list[str]:
    return value if isinstance(value, list) and all(isinstance(item, str) for item in value) else []


def matched_files(root: Path, globs: list[str]) -> list[Path]:
    matches: list[Path] = []
    for pattern in globs:
        matches.extend(sorted(root.glob(pattern)))
    return [path for path in matches if path.is_file()]


def check_reports(paths: list[Path], fail_regex: str | None, pass_regex: str | None) -> tuple[list[str], list[str]]:
    dirty: list[str] = []
    missing_clean_marker: list[str] = []
    if not fail_regex:
        fail_pattern = None
    else:
        fail_pattern = re.compile(fail_regex)
    pass_pattern = re.compile(pass_regex) if pass_regex else None
    for path in paths:
        text = path.read_text(errors="ignore")
        if fail_pattern and fail_pattern.search(text):
            dirty.append(str(path))
        if pass_pattern and not pass_pattern.search(text):
            missing_clean_marker.append(str(path))
    return dirty, missing_clean_marker


def validate_manifest(manifest_path: Path, manifest: dict) -> list[str]:
    failures: list[str] = []
    run_roots = as_list(manifest.get("run_roots"))
    required = manifest.get("required_artifacts")

    if not isinstance(manifest.get("signoff"), str) or not manifest["signoff"]:
        failures.append("manifest must name signoff")
    if not run_roots:
        failures.append("manifest must list run_roots")
    if not isinstance(required, dict):
        return failures + ["manifest has no required_artifacts"]

    missing = sorted(set(REQUIRED_ARTIFACTS) - set(required))
    extra = sorted(set(required) - set(REQUIRED_ARTIFACTS))
    if missing:
        failures.append("manifest missing required artifact classes: " + ", ".join(missing))
    if extra:
        failures.append("manifest has unknown artifact classes: " + ", ".join(extra))

    for run_root in run_roots:
        if Path(run_root).is_absolute() or ".." in Path(run_root).parts:
            failures.append(f"run_root must be a relative repo path: {run_root}")

    for name, spec in required.items():
        if not isinstance(spec, dict):
            failures.append(f"{name}: artifact spec must be a mapping")
            continue
        globs = as_list(spec.get("globs"))
        if not globs:
            failures.append(f"{name}: missing globs")
            continue
        extension = REQUIRED_ARTIFACTS.get(name)
        for pattern in globs:
            path = Path(pattern)
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"{name}: glob must be a relative repo path: {pattern}")
            if run_roots and not any(pattern.startswith(f"{run_root.rstrip('/')}/*/") for run_root in run_roots):
                failures.append(f"{name}: glob must be scoped to one configured run root: {pattern}")
            if extension and not pattern.endswith(extension):
                failures.append(f"{name}: glob must match {extension} files: {pattern}")
        if name.endswith("_report"):
            if not isinstance(spec.get("fail_regex"), str) or not spec["fail_regex"]:
                failures.append(f"{name}: report artifacts require fail_regex")
            if not isinstance(spec.get("pass_regex"), str) or not spec["pass_regex"]:
                failures.append(f"{name}: report artifacts require pass_regex")
        min_bytes = spec.get("min_bytes", 1)
        if not isinstance(min_bytes, int) or min_bytes < 1:
            failures.append(f"{name}: min_bytes must be a positive integer")

    waivers = manifest.get("waivers", {})
    if waivers and not isinstance(waivers, dict):
        failures.append("waivers must be a mapping")
    elif waivers:
        for pattern in as_list(waivers.get("globs")):
            path = Path(pattern)
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"waiver glob must be a relative repo path: {pattern}")

    if manifest_path.name != "manifest.yaml":
        failures.append("signoff manifest file must be named manifest.yaml")
    return failures


def run_dirs(root: Path, run_roots: list[str]) -> list[Path]:
    dirs: list[Path] = []
    for run_root in run_roots:
        base = root / run_root
        if base.is_dir():
            dirs.extend(sorted(path for path in base.iterdir() if path.is_dir()))
    return dirs


def files_for_run(run_dir: Path, run_root: str, globs: list[str]) -> list[Path]:
    files: list[Path] = []
    prefix = f"{run_root.rstrip('/')}/*/"
    for pattern in globs:
        if pattern.startswith(prefix):
            files.extend(sorted(path for path in run_dir.glob(pattern[len(prefix) :]) if path.is_file()))
    return files


def choose_complete_run(root: Path, manifest: dict) -> tuple[Path | None, dict[str, list[Path]], dict[Path, list[str]]]:
    required = manifest["required_artifacts"]
    run_roots = as_list(manifest["run_roots"])
    best_run: Path | None = None
    best_artifacts: dict[str, list[Path]] = {}
    missing_by_run: dict[Path, list[str]] = {}

    for run_dir in run_dirs(root, run_roots):
        run_root = str(run_dir.parent.relative_to(root))
        artifacts: dict[str, list[Path]] = {}
        missing: list[str] = []
        for name, spec in required.items():
            files = files_for_run(run_dir, run_root, spec["globs"])
            if files:
                artifacts[name] = files
            else:
                missing.append(name)
        missing_by_run[run_dir] = missing
        if best_run is None or len(missing) < len(missing_by_run[best_run]):
            best_run = run_dir
            best_artifacts = artifacts
        if not missing:
            return run_dir, artifacts, missing_by_run
    return None, best_artifacts, missing_by_run


def main() -> int:
    parser = ArgumentParser(description="Validate PD signoff artifact manifest.")
    parser.add_argument("--manifest", default="pd/signoff/manifest.yaml")
    parser.add_argument("--manifest-only", action="store_true", help="validate manifest shape without requiring run artifacts")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    manifest_path = root / args.manifest
    manifest = yaml.safe_load(manifest_path.read_text())
    if not isinstance(manifest, dict):
        print("PD signoff artifact check failed:")
        print("  - manifest must be a YAML mapping")
        return 1

    required = manifest.get("required_artifacts", {})
    failures = validate_manifest(manifest_path, manifest)
    dirty_reports: list[str] = []
    missing_clean_markers: list[str] = []

    if args.manifest_only or failures:
        if failures:
            print("PD signoff artifact check failed:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print("PD signoff manifest check ok")
        return 0

    run_roots = as_list(manifest["run_roots"])
    complete_run, artifacts, missing_by_run = choose_complete_run(root, manifest)
    if not missing_by_run:
        failures.append("no PD run directories found under run_roots: " + ", ".join(run_roots))
    elif complete_run is None:
        best_run = min(missing_by_run, key=lambda run: len(missing_by_run[run]))
        failures.append("no single PD run contains all required signoff artifacts")
        failures.append(
            f"closest run {best_run.relative_to(root)} missing: " + ", ".join(missing_by_run[best_run])
        )
    else:
        print(f"Checking PD signoff run: {complete_run.relative_to(root)}")
        for name, files in artifacts.items():
            spec = required[name]
            min_bytes = spec.get("min_bytes", 1)
            empty = [path for path in files if path.stat().st_size < min_bytes]
            for path in empty:
                failures.append(f"{name}: artifact is smaller than min_bytes={min_bytes}: {path.relative_to(root)}")
            if name.endswith("_report"):
                dirty, missing_clean = check_reports(files, spec.get("fail_regex"), spec.get("pass_regex"))
                dirty_reports.extend(dirty)
                missing_clean_markers.extend(missing_clean)

    waiver_spec = manifest.get("waivers", {})
    waivers = matched_files(root, waiver_spec.get("globs", []))
    if dirty_reports and waiver_spec.get("required_if_any_report_dirty", False) and not waivers:
        failures.append("dirty signoff reports found but no waiver file is present")
    for path in dirty_reports:
        failures.append(f"signoff report matched failure regex: {path}")
    for path in missing_clean_markers:
        failures.append(f"signoff report missing required clean marker: {path}")

    if failures:
        print("PD signoff artifact check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    mode = "manifest" if args.manifest_only else "artifacts"
    print(f"PD signoff {mode} check ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
