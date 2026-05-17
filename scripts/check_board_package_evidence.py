#!/usr/bin/env python3
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/manufacturing/board-package-evidence.yaml"
ALLOWED_STATUS = {"missing", "draft", "complete"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RELEASE_BLOCKER_IDS = {
    "package_drawing",
    "kicad_project",
    "kicad_schematic",
    "kicad_pcb",
    "erc",
    "drc",
    "gerbers",
    "drill",
    "bom",
    "pick_and_place",
    "dfm",
    "si_pi",
    "first_article",
}


def as_string_list(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value
    return []


def repo_path(path: str) -> Path:
    return ROOT / path


def matching_files(globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in globs:
        files.extend(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(files))


def validate_rel_path(field: str, value: str, failures: list[str]) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        failures.append(f"{field}: path must be repo-relative: {value}")


def validate_placeholder_blockers(manifest: dict, failures: list[str]) -> None:
    blockers = manifest.get("placeholder_blockers")
    if not isinstance(blockers, list) or not blockers:
        failures.append("placeholder_blockers: missing explicit placeholder blocker records")
        return
    for blocker in blockers:
        if not isinstance(blocker, dict):
            failures.append("placeholder_blockers: blocker must be a mapping")
            continue
        blocker_id = blocker.get("id", "<missing-id>")
        file_name = blocker.get("file")
        if not isinstance(file_name, str) or not file_name:
            failures.append(f"placeholder_blockers.{blocker_id}: missing file")
            continue
        validate_rel_path(f"placeholder_blockers.{blocker_id}.file", file_name, failures)
        path = repo_path(file_name)
        if not path.is_file():
            failures.append(f"placeholder_blockers.{blocker_id}: file is missing: {file_name}")
            continue
        text = path.read_text(errors="ignore")
        required_text = as_string_list(blocker.get("required_text"))
        if not required_text:
            failures.append(
                f"placeholder_blockers.{blocker_id}: required_text must be a non-empty string list"
            )
            continue
        missing_markers = [marker for marker in required_text if marker not in text]
        if missing_markers:
            failures.append(
                f"placeholder_blockers.{blocker_id}: missing placeholder marker(s): "
                + ", ".join(missing_markers)
            )


def validate_artifact(
    group_name: str,
    artifact: object,
    release: bool,
    failures: list[str],
    release_blockers: list[str],
    blocker_ids: set[str],
) -> None:
    if not isinstance(artifact, dict):
        failures.append(f"{group_name}: artifact must be a mapping")
        return
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        failures.append(f"{group_name}: artifact missing name")
        name = "unnamed"
    field = f"{group_name}.{name}"
    status = artifact.get("status")
    if status not in ALLOWED_STATUS:
        failures.append(f"{field}: status must be missing, draft, or complete")
    globs = as_string_list(artifact.get("globs"))
    if not globs:
        failures.append(f"{field}: globs must be a non-empty string list")
    for pattern in globs:
        validate_rel_path(f"{field}.globs", pattern, failures)

    metadata = artifact.get("metadata", {})
    if metadata and not isinstance(metadata, dict):
        failures.append(f"{field}: metadata must be a mapping")
        metadata = {}
    required_metadata = as_string_list(artifact.get("required_metadata", []))
    if artifact.get("required_metadata", []) and not required_metadata:
        failures.append(f"{field}: required_metadata must be a string list")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if key.endswith("_sha256") and (
                not isinstance(value, str) or not SHA256_RE.fullmatch(value)
            ):
                failures.append(f"{field}.metadata.{key}: must be lowercase sha256")
    if (release or status == "complete") and required_metadata:
        present = set(metadata) if isinstance(metadata, dict) else set()
        missing = sorted(set(required_metadata) - present)
        if missing:
            failures.append(f"{field}: missing required metadata: " + ", ".join(missing))

    files = matching_files(globs)
    blocker = artifact.get("release_blocker")
    blocker_id = artifact.get("release_blocker_id")
    if blocker is not None and (not isinstance(blocker, str) or not blocker):
        failures.append(f"{field}: release_blocker must be a non-empty string")
    if blocker_id is not None:
        if not isinstance(blocker_id, str) or not blocker_id:
            failures.append(f"{field}: release_blocker_id must be a non-empty string")
        else:
            blocker_ids.add(blocker_id)
    if status == "missing" and files:
        failures.append(f"{field}: status missing but files exist")
    if status == "complete" and not files:
        failures.append(f"{field}: status complete but files are missing")
    if release:
        if isinstance(blocker, str) and blocker and (status != "complete" or not files):
            if isinstance(blocker_id, str) and blocker_id:
                release_blockers.append(f"{blocker_id}: {blocker}")
            else:
                release_blockers.append(blocker)
        if status != "complete":
            failures.append(f"{field}: release requires status complete, got {status}")
        if not files:
            failures.append(f"{field}: release artifact files are missing")


def validate_manifest(release: bool, release_blockers: list[str]) -> list[str]:
    failures: list[str] = []
    blocker_ids: set[str] = set()
    if not MANIFEST.is_file():
        return [f"missing manifest: {MANIFEST.relative_to(ROOT)}"]
    try:
        manifest = yaml.safe_load(MANIFEST.read_text())
    except yaml.YAMLError as exc:
        return [f"{MANIFEST.relative_to(ROOT)}: invalid YAML: {exc}"]
    if not isinstance(manifest, dict):
        return [f"{MANIFEST.relative_to(ROOT)}: manifest must be a mapping"]

    if manifest.get("status") != "release_blocked":
        failures.append(
            "manifest status must remain release_blocked until real artifacts are complete"
        )
    if manifest.get("release_gate") != "board_fabrication_release":
        failures.append("release_gate must be board_fabrication_release")

    validate_placeholder_blockers(manifest, failures)

    groups = manifest.get("artifact_groups")
    if not isinstance(groups, dict) or not groups:
        failures.append("artifact_groups: missing evidence groups")
        return failures
    for group_name, group in groups.items():
        if not isinstance(group, dict):
            failures.append(f"artifact_groups.{group_name}: group must be a mapping")
            continue
        group_status = group.get("status")
        if group_status not in ALLOWED_STATUS:
            failures.append(
                f"artifact_groups.{group_name}: status must be missing, draft, or complete"
            )
        if release and group_status != "complete":
            failures.append(
                f"artifact_groups.{group_name}: release requires status complete, got {group_status}"
            )
        artifacts = group.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            failures.append(f"artifact_groups.{group_name}: missing artifacts")
            continue
        for artifact in artifacts:
            validate_artifact(
                f"artifact_groups.{group_name}",
                artifact,
                release,
                failures,
                release_blockers,
                blocker_ids,
            )

    missing_blocker_ids = sorted(REQUIRED_RELEASE_BLOCKER_IDS - blocker_ids)
    if missing_blocker_ids:
        failures.append("missing required release blocker ids: " + ", ".join(missing_blocker_ids))

    return failures


def unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def main() -> int:
    parser = ArgumentParser(description="Validate board/package/vendor/fab evidence manifest.")
    parser.add_argument("--release", action="store_true", help="require release-complete evidence")
    args = parser.parse_args()

    release_blockers: list[str] = []
    failures = validate_manifest(args.release, release_blockers)
    if failures:
        mode = "release" if args.release else "preflight"
        print(f"board/package evidence {mode} check failed:")
        if args.release and release_blockers:
            print("Release blockers:")
            for blocker in unique_items(release_blockers):
                print(f"  - {blocker}")
            print("Validation detail:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    mode = "release" if args.release else "preflight"
    print(f"board/package evidence {mode} check ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
