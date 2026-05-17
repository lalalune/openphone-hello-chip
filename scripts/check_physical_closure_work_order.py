#!/usr/bin/env python3
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORK_ORDER = ROOT / "docs/manufacturing/physical-closure-work-order.yaml"
GAP_MANIFEST = ROOT / "docs/manufacturing/real-world-verification-gaps.yaml"

REQUIRED_GATES = {"pd_release", "tapeout_release", "board_fabrication_release"}
REQUIRED_ITEM_FIELDS = {
    "id",
    "gate",
    "owner",
    "artifact_names",
    "evidence_paths",
    "acceptance_criteria",
}
FORBIDDEN_LOCAL_CLAIMS = {
    "Tapeout ready.",
    "Board fabrication ready.",
    "Foundry padframe approved.",
    "Package vendor approved.",
    "Lab verified.",
    "SI/PI closed.",
    "IR-drop or EM closed.",
    "Thermal closed.",
}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} must be a YAML mapping")
    return data


def is_relative_path_like(value: str) -> bool:
    path = Path(value.replace("<selected-run>", "selected-run"))
    return not path.is_absolute() and ".." not in path.parts


def validate_text_list(label: str, value: object, min_len: int, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or len(value) < min_len:
        failures.append(f"{label} must list at least {min_len} item(s)")
        return []
    strings = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            failures.append(f"{label}[{index}] must be a non-empty string")
        else:
            strings.append(item)
    return strings


def main() -> int:
    failures: list[str] = []
    work_order = load_yaml(WORK_ORDER)
    gap_manifest = load_yaml(GAP_MANIFEST)

    if work_order.get("status") != "release_blocked":
        failures.append("work order status must stay release_blocked until physical evidence is archived")
    if work_order.get("source_gap_manifest") != "docs/manufacturing/real-world-verification-gaps.yaml":
        failures.append("work order must point at docs/manufacturing/real-world-verification-gaps.yaml")

    claim_policy = work_order.get("claim_policy")
    if not isinstance(claim_policy, dict):
        failures.append("work order must define claim_policy")
    else:
        allowed = validate_text_list("claim_policy.allowed_local_claims", claim_policy.get("allowed_local_claims"), 2, failures)
        forbidden = set(validate_text_list("claim_policy.forbidden_claims_until_evidence_archived", claim_policy.get("forbidden_claims_until_evidence_archived"), 4, failures))
        missing_forbidden = sorted(FORBIDDEN_LOCAL_CLAIMS - forbidden)
        if missing_forbidden:
            failures.append("claim_policy missing forbidden claims: " + ", ".join(missing_forbidden))
        if not any("Machine checks prove only" in item for item in allowed):
            failures.append("claim_policy must limit local machine-check claims")

    validate_text_list("global_acceptance", work_order.get("global_acceptance"), 4, failures)

    gaps = gap_manifest.get("gaps")
    if not isinstance(gaps, list):
        failures.append("gap manifest must list gaps")
        gaps = []
    gap_by_id = {
        gap.get("id"): gap
        for gap in gaps
        if isinstance(gap, dict) and isinstance(gap.get("id"), str)
    }

    items = work_order.get("items")
    if not isinstance(items, list) or not items:
        failures.append("work order must list items")
        items = []

    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            failures.append(f"{label} must be a mapping")
            continue
        missing_fields = sorted(REQUIRED_ITEM_FIELDS - set(item))
        if missing_fields:
            failures.append(f"{label} missing fields: " + ", ".join(missing_fields))

        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            failures.append(f"{label}.id must be a non-empty string")
            item_id = label
        if item_id in seen_ids:
            failures.append(f"{label} duplicate item id: {item_id}")
        seen_ids.add(item_id)

        gap = gap_by_id.get(item_id)
        if gap is None:
            failures.append(f"{item_id}: no matching gap in real-world verification manifest")
        elif item.get("gate") != gap.get("release_gate"):
            failures.append(f"{item_id}: gate must match gap release_gate {gap.get('release_gate')}")

        if item.get("gate") not in REQUIRED_GATES:
            failures.append(f"{item_id}: invalid gate")

        artifact_names = validate_text_list(f"{item_id}.artifact_names", item.get("artifact_names"), 2, failures)
        for artifact in artifact_names:
            if any(token in artifact.upper() for token in ("TBD", "TODO", "PLACEHOLDER")):
                failures.append(f"{item_id}.artifact_names must not contain placeholder token: {artifact}")

        evidence_paths = validate_text_list(f"{item_id}.evidence_paths", item.get("evidence_paths"), 1, failures)
        for evidence_path in evidence_paths:
            if not is_relative_path_like(evidence_path):
                failures.append(f"{item_id}.evidence_paths must be relative repo paths: {evidence_path}")

        criteria = validate_text_list(f"{item_id}.acceptance_criteria", item.get("acceptance_criteria"), 2, failures)
        if not any(("clean" in criterion.lower() or "waiv" in criterion.lower() or "pass" in criterion.lower()) for criterion in criteria):
            failures.append(f"{item_id}.acceptance_criteria must include pass, clean, or waiver language")

    missing_items = sorted(set(gap_by_id) - seen_ids)
    extra_items = sorted(seen_ids - set(gap_by_id))
    if missing_items:
        failures.append("work order missing gap item(s): " + ", ".join(missing_items))
    if extra_items:
        failures.append("work order contains non-gap item(s): " + ", ".join(extra_items))

    if failures:
        print("Physical closure work-order check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("physical closure work order ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
