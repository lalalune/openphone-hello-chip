#!/usr/bin/env python3
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"
EVIDENCE_MANIFEST = ROOT / "docs/evidence/software-bsp-evidence-manifest.json"
EVIDENCE_SCHEMA = ROOT / "docs/evidence/software-bsp-evidence.schema.json"
AOSP_EVIDENCE_MANIFEST = ROOT / "sw/aosp-device/evidence_manifest.json"
AOSP_EVIDENCE_SCHEMA = ROOT / "docs/evidence/aosp-evidence.schema.json"

DEFAULT_FORBIDDEN_EVIDENCE_TERMS = [
    "placeholder",
    "template only",
    "sample only",
    "not real evidence",
    "todo",
    "fake",
    "synthetic evidence",
    "openphone-evidence: template=true",
    "openphone-evidence: status=FAIL",
    "openphone-evidence: status=BLOCKED",
]

EVIDENCE_ITEM_KEYS = {
    "artifact",
    "path",
    "claim_boundary",
    "capture_command",
    "validation_command",
    "external_artifacts",
    "min_bytes",
    "required_strings",
    "at_least_one",
    "forbidden_strings",
}
EVIDENCE_PATH_RE = re.compile(r"^docs/evidence/(buildroot|linux|android)/[^/]+\.(log|txt)$")
STATUS_RE = re.compile(r"^openphone-evidence:\s*status=([^\s]+).*$", re.MULTILINE)
AOSP_REFERENCE_ONLY_BOUNDARY = "reference_only_not_hello_chip_ap_evidence"
AOSP_REFERENCE_ONLY_PATHS = {
    "docs/evidence/android/cuttlefish_riscv64_boot.log",
    "docs/evidence/android/cts_virtual_device_subset.log",
    "docs/evidence/android/vts_virtual_device_subset.log",
}


class TargetSpec(TypedDict, total=False):
    readme: Path
    required: list[str]
    contract_terms: list[str]
    evidence: list[str]
    evidence_note: str
    scaffold_audit: str


TARGETS: dict[str, TargetSpec] = {
    "buildroot": {
        "readme": ROOT / "docs/sw/buildroot/README.md",
        "required": [
            "sw/buildroot/external.desc",
            "sw/buildroot/Config.in",
            "sw/buildroot/external.mk",
            "sw/buildroot/scripts/import-buildroot-external.sh",
            "sw/buildroot/configs/openphone_hello_defconfig",
            "sw/buildroot/board/openphone/hello/linux.fragment",
            "sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke",
        ],
        "contract_terms": [
            "BR2_EXTERNAL_OPENPHONE_HELLO_PATH",
            "HELLO_NPU_BASE",
            "HELLO_DISPLAY_BASE",
            "HELLO_DMA_BASE",
        ],
        "evidence": [
            "docs/evidence/buildroot/openphone_hello_defconfig.log",
            "docs/evidence/buildroot/openphone_hello_image_manifest.txt",
            "docs/evidence/buildroot/hello-mmio-smoke.log",
        ],
        "evidence_note": "external Buildroot image build plus hello MMIO smoke transcript",
    },
    "linux": {
        "readme": ROOT / "docs/sw/linux/README.md",
        "required": [
            "sw/linux/drivers/hello/Kconfig",
            "sw/linux/drivers/hello/Makefile",
            "sw/linux/scripts/import-linux-bsp.sh",
            "sw/linux/dts/openphone-hello.dts",
            "sw/linux/drivers/hello/hello_platform_contract.h",
            "sw/linux/drivers/hello/hello-npu.c",
            "sw/linux/drivers/hello/hello-dma.c",
            "sw/linux/tests/hello-mmio-smoke.c",
        ],
        "contract_terms": [
            "CONFIG_OPENPHONE_HELLO_NPU",
            "CONFIG_OPENPHONE_HELLO_DMA",
            "openphone,hello-npu",
            "openphone,hello-dma",
            "openphone,hello-display",
            '#include "hello_platform_contract.h"',
        ],
        "evidence": [
            "docs/evidence/linux/openphone_hello_kernel_build.log",
            "docs/evidence/linux/openphone_hello_dtb_check.log",
            "docs/evidence/linux/hello-mmio-smoke.log",
        ],
        "evidence_note": "external Linux kernel build, DTB validation, and runtime driver smoke transcript",
    },
    "opensbi": {
        "readme": ROOT / "docs/sw/opensbi/README.md",
        "required": [
            "docs/sw/opensbi/README.md",
            "sw/opensbi/capture-opensbi-evidence.sh",
        ],
        "contract_terms": [
            "sw/platform/hello_platform_contract.json",
            "dependency blocker",
            "OpenSBI",
            "CPU-capable",
        ],
        "evidence": [
            "docs/evidence/linux/opensbi_openphone_build.log",
            "docs/evidence/linux/opensbi_fw_dynamic_handoff.log",
        ],
        "evidence_note": "external OpenSBI build and fw_dynamic handoff transcript",
        "scaffold_audit": "boot",
    },
    "u-boot": {
        "readme": ROOT / "docs/sw/u-boot/README.md",
        "required": [
            "docs/sw/u-boot/README.md",
            "sw/u-boot/capture-u-boot-evidence.sh",
        ],
        "contract_terms": [
            "sw/platform/hello_platform_contract.json",
            "dependency blocker",
            "U-Boot",
            "OpenSBI handoff",
        ],
        "evidence": [
            "docs/evidence/linux/u_boot_openphone_build.log",
            "docs/evidence/linux/u_boot_opensbi_boot_chain.log",
        ],
        "evidence_note": "external U-Boot build and OpenSBI-to-U-Boot boot-chain transcript",
        "scaffold_audit": "boot",
    },
    "aosp": {
        "readme": ROOT / "docs/sw/aosp-device/README.md",
        "required": [
            "sw/aosp-device/import-aosp-device.sh",
            "sw/aosp-device/capture-aosp-evidence.sh",
            "sw/aosp-device/evidence_manifest.json",
            "sw/aosp-device/manifests/openphone-ai-soc-local.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
            "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
            "docs/sw/aosp-device/device/openphone/openphone_ai_soc/hal/README.md",
        ],
        "contract_terms": ["openphone_ai_soc", "hello_npu", "hwcomposer"],
        "evidence": [
            "docs/evidence/android/openphone_ai_soc_lunch.log",
            "docs/evidence/android/openphone_ai_soc_vendorimage.log",
            "docs/evidence/android/openphone_ai_soc_checkvintf.log",
            "docs/evidence/android/cuttlefish_riscv64_boot.log",
            "docs/evidence/android/cts_virtual_device_subset.log",
            "docs/evidence/android/vts_virtual_device_subset.log",
        ],
        "evidence_note": "external AOSP lunch/vendorimage/VINTF logs, Cuttlefish or equivalent boot transcript, and Android compatibility subset transcripts",
    },
}


def load_json_no_duplicate_keys(path: Path, errors: list[str]) -> dict:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
        seen: set[str] = set()
        data: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError(f"duplicate JSON key {key!r}")
            seen.add(key)
            data[key] = value
        return data

    try:
        return json.loads(path.read_text(), object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
    except ValueError as exc:
        errors.append(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
    return {}


def validate_string_list(
    value: object, path: str, errors: list[str], *, min_items: int = 0
) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return
    if len(value) < min_items:
        errors.append(f"{path} must contain at least {min_items} item(s)")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{path}[{index}] must be a non-empty string")


def validate_evidence_manifest_schema(data: object, errors: list[str]) -> None:
    rel = EVIDENCE_MANIFEST.relative_to(ROOT)
    if not isinstance(data, dict):
        errors.append(f"{rel} must be a JSON object")
        return

    allowed_top = {"schema_version", "claim_boundary", "targets"}
    extra_top = sorted(set(data) - allowed_top)
    if extra_top:
        errors.append(f"{rel} has unsupported top-level keys: " + ", ".join(extra_top))
    for key in allowed_top:
        if key not in data:
            errors.append(f"{rel} missing required key {key}")

    targets = data.get("targets")
    if not isinstance(targets, dict):
        errors.append(f"{rel} targets must be an object")
        return
    missing_targets = sorted(set(TARGETS) - set(targets))
    extra_targets = sorted(set(targets) - set(TARGETS))
    if missing_targets:
        errors.append(f"{rel} missing targets: " + ", ".join(missing_targets))
    if extra_targets:
        errors.append(f"{rel} has unsupported targets: " + ", ".join(extra_targets))

    seen_paths: dict[str, str] = {}
    for target, target_data in targets.items():
        target_path = f"{rel}:targets.{target}"
        if not isinstance(target_data, dict):
            errors.append(f"{target_path} must be an object")
            continue
        extra_target_keys = sorted(set(target_data) - {"evidence"})
        if extra_target_keys:
            errors.append(f"{target_path} has unsupported keys: " + ", ".join(extra_target_keys))
        items = target_data.get("evidence")
        if not isinstance(items, list) or not items:
            errors.append(f"{target_path}.evidence must be a non-empty list")
            continue
        for index, item in enumerate(items):
            item_path = f"{target_path}.evidence[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_path} must be an object")
                continue
            extra_item_keys = sorted(set(item) - EVIDENCE_ITEM_KEYS)
            if extra_item_keys:
                errors.append(f"{item_path} has unsupported keys: " + ", ".join(extra_item_keys))
            for key in (
                "artifact",
                "path",
                "capture_command",
                "validation_command",
                "min_bytes",
                "required_strings",
            ):
                if key not in item:
                    errors.append(f"{item_path} missing required key {key}")
            artifact = item.get("artifact")
            if not isinstance(artifact, str) or not artifact:
                errors.append(f"{item_path}.artifact must be a non-empty string")
            path = item.get("path")
            if not isinstance(path, str) or not EVIDENCE_PATH_RE.match(path):
                errors.append(f"{item_path}.path must be a docs/evidence log or txt path")
            elif path in seen_paths:
                errors.append(f"{item_path}.path duplicates {seen_paths[path]}: {path}")
            elif target in TARGETS and path not in TARGETS[target]["evidence"]:
                errors.append(f"{item_path}.path is not valid for target {target}: {path}")
            elif isinstance(path, str):
                seen_paths[path] = item_path
            for key in ("capture_command", "validation_command"):
                value = item.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{item_path}.{key} must be a non-empty string")
            validation = item.get("validation_command")
            if isinstance(validation, str) and (
                "scripts/check_software_bsp.py" not in validation
                or target not in validation
                or "--require-evidence" not in validation
            ):
                errors.append(
                    f"{item_path}.validation_command must run the fail-closed BSP evidence check"
                )
            min_bytes = item.get("min_bytes")
            if not isinstance(min_bytes, int) or min_bytes < 80:
                errors.append(f"{item_path}.min_bytes must be an integer >= 80")
            validate_string_list(
                item.get("required_strings"),
                f"{item_path}.required_strings",
                errors,
                min_items=1,
            )
            if "forbidden_strings" in item:
                validate_string_list(
                    item.get("forbidden_strings"), f"{item_path}.forbidden_strings", errors
                )
            if "external_artifacts" in item:
                validate_string_list(
                    item.get("external_artifacts"),
                    f"{item_path}.external_artifacts",
                    errors,
                    min_items=1,
                )
            if target == "aosp" and "external_artifacts" not in item:
                errors.append(f"{item_path}.external_artifacts is required for AOSP evidence")
            claim_boundary = item.get("claim_boundary")
            if path in AOSP_REFERENCE_ONLY_PATHS:
                if claim_boundary != AOSP_REFERENCE_ONLY_BOUNDARY:
                    errors.append(
                        f"{item_path}.claim_boundary must be {AOSP_REFERENCE_ONLY_BOUNDARY}"
                    )
                required_strings = item.get("required_strings", [])
                boundary_marker = (
                    f"openphone-evidence: claim_boundary={AOSP_REFERENCE_ONLY_BOUNDARY}"
                )
                if isinstance(required_strings, list) and boundary_marker not in required_strings:
                    errors.append(f"{item_path}.required_strings must require {boundary_marker}")
            elif claim_boundary is not None:
                errors.append(
                    f"{item_path}.claim_boundary is only valid for reference-only AOSP evidence"
                )
            if "at_least_one" in item:
                groups = item.get("at_least_one")
                if not isinstance(groups, list) or not groups:
                    errors.append(f"{item_path}.at_least_one must be a non-empty list")
                else:
                    for group_index, group in enumerate(groups):
                        validate_string_list(
                            group,
                            f"{item_path}.at_least_one[{group_index}]",
                            errors,
                            min_items=1,
                        )


def check_contract(errors: list[str]) -> None:
    if not CONTRACT.is_file():
        errors.append("sw/platform/hello_platform_contract.json is missing")
        return
    data = json.loads(CONTRACT.read_text())
    if data.get("hello_chip", {}).get("has_cpu") is not False:
        errors.append(
            "hello platform contract must keep hello_chip.has_cpu=false until a CPU exists"
        )
    if data.get("qemu_virt", {}).get("target_kind") != "software_reference_only":
        errors.append("qemu_virt must be marked software_reference_only")


def check_aosp_product_glue(errors: list[str]) -> None:
    product = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk"
    board = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk"
    manifest = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml"
    text = product.read_text(errors="ignore") if product.is_file() else ""
    if "COMMON_LUNCH_CHOICES" not in text or "openphone_ai_soc-userdebug" not in text:
        errors.append("AOSP AndroidProducts.mk must expose openphone_ai_soc-userdebug lunch")
    board_text = board.read_text(errors="ignore") if board.is_file() else ""
    for term in [
        "TARGET_ARCH := riscv64",
        "BOARD_VENDOR_SEPOLICY_DIRS",
        "OPENPHONE_KERNEL_CONFIG_FRAGMENT",
        "OPENPHONE_DTS",
    ]:
        if term not in board_text:
            errors.append(f"AOSP BoardConfig.mk missing {term}")
    if manifest.is_file():
        manifest_text = manifest.read_text(errors="ignore")
        for term in ["<manifest", "</manifest>", "hello_npu", "hwcomposer.openphone_ai_soc"]:
            if term not in manifest_text:
                errors.append(f"AOSP VINTF manifest missing XML marker {term}")
        if "<hal" in manifest_text:
            errors.append(
                "AOSP VINTF manifest must not declare active HAL entries until source or prebuilts exist"
            )
    device = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk"
    device_text = device.read_text(errors="ignore") if device.is_file() else ""
    if "PRODUCT_PACKAGES +=" in device_text and (
        "hello_npu.default" in device_text or "hwcomposer.openphone_ai_soc" in device_text
    ):
        errors.append("AOSP device.mk must not list HAL packages until source or prebuilts exist")


def load_evidence_manifest(errors: list[str]) -> dict:
    if not EVIDENCE_SCHEMA.is_file():
        errors.append(f"{EVIDENCE_SCHEMA.relative_to(ROOT)} is missing")
    else:
        load_json_no_duplicate_keys(EVIDENCE_SCHEMA, errors)
    if not EVIDENCE_MANIFEST.is_file():
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} is missing")
        return {}
    data = load_json_no_duplicate_keys(EVIDENCE_MANIFEST, errors)
    if not data:
        return {}
    if data.get("schema_version") != 1:
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} must have schema_version=1")
    if data.get("claim_boundary") != "external_transcripts_only":
        errors.append(
            f"{EVIDENCE_MANIFEST.relative_to(ROOT)} must use claim_boundary=external_transcripts_only"
        )
    validate_evidence_manifest_schema(data, errors)
    return data


def validate_manifest_item(target: str, item: dict, errors: list[str]) -> None:
    path = item.get("path")
    if not isinstance(path, str) or not path.startswith("docs/evidence/"):
        errors.append(f"{target} evidence item has invalid repo-relative path: {path!r}")
    elif path not in TARGETS[target]["evidence"]:
        errors.append(
            f"{target} evidence item path is not listed in checker target evidence: {path}"
        )
    for key in (
        "artifact",
        "capture_command",
        "validation_command",
        "min_bytes",
        "required_strings",
    ):
        if key not in item:
            errors.append(f"{target} evidence item {path or '<unknown>'} missing {key}")
    validation = item.get("validation_command")
    if isinstance(validation, str) and (
        "scripts/check_software_bsp.py" not in validation
        or target not in validation
        or "--require-evidence" not in validation
    ):
        errors.append(
            f"{target} evidence item {path or '<unknown>'} validation_command must run the fail-closed BSP evidence check"
        )
    if not isinstance(item.get("required_strings", []), list):
        errors.append(
            f"{target} evidence item {path or '<unknown>'} required_strings must be a list"
        )
    elif not item.get("required_strings", []):
        errors.append(
            f"{target} evidence item {path or '<unknown>'} required_strings must not be empty"
        )
    if not isinstance(item.get("min_bytes", 0), int) or item.get("min_bytes", 0) < 80:
        errors.append(f"{target} evidence item {path or '<unknown>'} min_bytes must be >= 80")
    if not isinstance(item.get("at_least_one", []), list):
        errors.append(f"{target} evidence item {path or '<unknown>'} at_least_one must be a list")
    if not isinstance(item.get("external_artifacts", []), list):
        errors.append(
            f"{target} evidence item {path or '<unknown>'} external_artifacts must be a list"
        )
    if target == "aosp":
        external_artifacts = item.get("external_artifacts")
        if not isinstance(external_artifacts, list) or not external_artifacts:
            errors.append(
                f"{target} evidence item {path or '<unknown>'} must list exact external_artifacts"
            )
        elif not all(isinstance(artifact, str) and artifact for artifact in external_artifacts):
            errors.append(
                f"{target} evidence item {path or '<unknown>'} external_artifacts must be non-empty strings"
            )


def evidence_items_for(target: str, manifest: dict, errors: list[str]) -> list[dict]:
    targets = manifest.get("targets", {})
    if target not in targets:
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} missing target {target}")
        return []
    items = targets[target].get("evidence", [])
    if not isinstance(items, list) or not items:
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} target {target} has no evidence list")
        return []
    for item in items:
        if isinstance(item, dict):
            validate_manifest_item(target, item, errors)
        else:
            errors.append(f"{target} evidence item must be an object: {item!r}")
    return [item for item in items if isinstance(item, dict)]


def load_aosp_evidence_manifest(errors: list[str]) -> dict:
    if not AOSP_EVIDENCE_SCHEMA.is_file():
        errors.append(f"{AOSP_EVIDENCE_SCHEMA.relative_to(ROOT)} is missing")
    else:
        load_json_no_duplicate_keys(AOSP_EVIDENCE_SCHEMA, errors)
    if not AOSP_EVIDENCE_MANIFEST.is_file():
        errors.append(f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} is missing")
        return {}
    return load_json_no_duplicate_keys(AOSP_EVIDENCE_MANIFEST, errors)


def check_aosp_evidence_manifest(errors: list[str]) -> None:
    data = load_aosp_evidence_manifest(errors)
    if not data:
        return
    if data.get("claim_boundary") != "android_external_logs_only":
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} must use claim_boundary=android_external_logs_only"
        )
    if data.get("compatibility_claim") != "none_without_cts_vts_logs":
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} must not claim Android compatibility without CTS/VTS logs"
        )
    if data.get("android_boot_claim") != "blocked_until_all_required_evidence_passes":
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} must block Android boot claims until all required evidence passes"
        )
    required_for_boot = data.get("required_for_android_boot_claim", [])
    if not isinstance(required_for_boot, list) or sorted(required_for_boot) != sorted(
        TARGETS["aosp"]["evidence"]
    ):
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} required_for_android_boot_claim must match required AOSP evidence paths"
        )
    forbidden_claims = data.get("forbidden_claims_without_required_evidence", [])
    if not isinstance(forbidden_claims, list) or not forbidden_claims:
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} must list forbidden Android boot/compatibility claims"
        )
    items = data.get("evidence", [])
    if not isinstance(items, list) or not items:
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} must list Android evidence paths"
        )
        return
    paths = [item.get("path") for item in items if isinstance(item, dict)]
    missing = [path for path in TARGETS["aosp"]["evidence"] if path not in paths]
    if missing:
        errors.append(
            f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} does not enumerate required Android evidence paths: "
            + ", ".join(missing)
        )
    for item in items:
        if not isinstance(item, dict):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item must be an object: {item!r}"
            )
            continue
        path = item.get("path")
        if not isinstance(path, str):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item has invalid path: {path!r}"
            )
            continue
        if path not in TARGETS["aosp"]["evidence"]:
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} has unexpected Android evidence path: {path}"
            )
        claim = item.get("claim")
        if not isinstance(claim, str) or not claim:
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} missing claim"
            )
        external_artifacts = item.get("external_artifacts")
        if not isinstance(external_artifacts, list) or not external_artifacts:
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} missing external_artifacts"
            )
        claim_boundary = item.get("claim_boundary")
        if path in AOSP_REFERENCE_ONLY_PATHS:
            if claim_boundary != AOSP_REFERENCE_ONLY_BOUNDARY:
                errors.append(
                    f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} must set claim_boundary={AOSP_REFERENCE_ONLY_BOUNDARY}"
                )
            if not isinstance(claim, str) or "reference" not in claim.lower():
                errors.append(
                    f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} claim must describe reference-only scope"
                )
        elif claim_boundary is not None:
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} has unexpected claim_boundary"
            )
        central_item = next(
            (
                central
                for central in evidence_items_for("aosp", load_evidence_manifest([]), [])
                if central.get("path") == path
            ),
            {},
        )
        if central_item and item.get("capture_command") != central_item.get("capture_command"):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} capture_command does not match central evidence manifest"
            )
        if central_item and item.get("validation_command") != central_item.get(
            "validation_command"
        ):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} validation_command does not match central evidence manifest"
            )
        if central_item and item.get("external_artifacts") != central_item.get(
            "external_artifacts"
        ):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} external_artifacts does not match central evidence manifest"
            )
        if central_item and item.get("claim_boundary") != central_item.get("claim_boundary"):
            errors.append(
                f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} evidence item {path} claim_boundary does not match central evidence manifest"
            )


def check_aosp_forbidden_claims(evidence_items: list[dict], blockers: list[str]) -> None:
    errors: list[str] = []
    manifest = load_aosp_evidence_manifest(errors)
    if errors or not manifest:
        return

    required_paths = manifest.get("required_for_android_boot_claim", TARGETS["aosp"]["evidence"])
    missing_required = [path for path in required_paths if not (ROOT / path).is_file()]
    if not missing_required:
        return

    forbidden_claims = manifest.get("forbidden_claims_without_required_evidence", [])
    if not isinstance(forbidden_claims, list) or not forbidden_claims:
        return

    for item in evidence_items:
        rel = item.get("path")
        if not isinstance(rel, str):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore").lower()
        found = [
            claim for claim in forbidden_claims if isinstance(claim, str) and claim.lower() in text
        ]
        if found:
            blockers.append(
                f"{rel} contains Android boot/compatibility claim before required evidence set is complete: "
                + ", ".join(found)
            )


def validate_evidence_file(item: dict) -> list[str]:
    rel = item["path"]
    path = ROOT / rel
    problems: list[str] = []
    if not path.is_file():
        return [f"missing {rel}; capture command: {item.get('capture_command', '<missing>')}"]

    text = path.read_text(errors="ignore")
    if len(text.strip()) < int(item.get("min_bytes", 80)):
        problems.append(f"{rel} is too small to be an external command transcript")

    status_lines = STATUS_RE.findall(text)
    if not status_lines:
        problems.append(f"{rel} missing openphone-evidence status line")
    elif len(status_lines) > 1:
        problems.append(f"{rel} has multiple openphone-evidence status lines")
    elif status_lines[0] != "PASS":
        problems.append(f"{rel} reports non-PASS evidence status: {status_lines[0]}")

    if "openphone-evidence: command=" not in text:
        problems.append(f"{rel} missing openphone-evidence command marker")
    if not ("openphone-evidence: ended_utc=" in text or "openphone-evidence: end_utc=" in text):
        problems.append(f"{rel} missing openphone-evidence end timestamp")
    claim_boundary = item.get("claim_boundary")
    if isinstance(claim_boundary, str) and claim_boundary:
        marker = f"openphone-evidence: claim_boundary={claim_boundary}"
        if marker not in text:
            problems.append(f"{rel} missing reference-only claim boundary marker: {marker}")

    forbidden = DEFAULT_FORBIDDEN_EVIDENCE_TERMS + item.get("forbidden_strings", [])
    lower = text.lower()
    found_forbidden = [term for term in forbidden if term.lower() in lower]
    if found_forbidden:
        problems.append(
            f"{rel} contains forbidden placeholder/failure markers: " + ", ".join(found_forbidden)
        )

    missing = [term for term in item.get("required_strings", []) if term not in text]
    if missing:
        problems.append(f"{rel} missing required transcript markers: " + ", ".join(missing))

    for group in item.get("at_least_one", []):
        if not isinstance(group, list) or not group:
            problems.append(f"{rel} has invalid at_least_one rule in manifest")
        elif not any(term in text for term in group):
            problems.append(f"{rel} must contain at least one marker from: " + ", ".join(group))

    return problems


def print_evidence_plan(targets: list[str]) -> int:
    errors: list[str] = []
    manifest = load_evidence_manifest(errors)
    if not manifest:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    failed = False
    for target in targets:
        items = evidence_items_for(target, manifest, errors)
        print(f"{target}: external evidence capture plan")
        print(f"  claim boundary: {manifest.get('claim_boundary')}")
        for item in items:
            path = item.get("path", "<missing>")
            problems = validate_evidence_file(item)
            status = "ready" if not problems else "blocked"
            print(f"  - {item.get('artifact', '<missing artifact>')}")
            print(f"    path: {path}")
            print(f"    capture: {item.get('capture_command', '<missing>')}")
            print(f"    validate: {item.get('validation_command', '<missing>')}")
            print(f"    required markers: {', '.join(item.get('required_strings', []))}")
            if item.get("at_least_one"):
                groups = [" | ".join(group) for group in item["at_least_one"]]
                print(f"    at least one marker: {'; '.join(groups)}")
            if item.get("forbidden_strings"):
                print(f"    forbidden markers: {', '.join(item['forbidden_strings'])}")
            print(f"    current status: {status}")
            if problems:
                failed = True
                for problem in problems:
                    print(f"      {problem}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


def evidence_validation_status(item: dict) -> tuple[str, list[str]]:
    problems = validate_evidence_file(item)
    if not problems:
        return "PASS", []
    if problems[0].startswith("missing "):
        return "MISSING", problems
    return "INVALID", problems


def target_names_from_arg(target: str) -> list[str]:
    return list(TARGETS.keys()) if target == "all" else [target]


def print_status(target: str) -> int:
    errors: list[str] = []
    manifest = load_evidence_manifest(errors)
    if errors:
        print("software BSP evidence manifest invalid:")
        for error in errors:
            print(f"  - {error}")
        return 1

    blocked = False
    for name in target_names_from_arg(target):
        print(f"{name}:")
        for item in evidence_items_for(name, manifest, errors):
            status, problems = evidence_validation_status(item)
            if status != "PASS":
                blocked = True
            print(f"  [{status}] {item.get('artifact', '<missing artifact>')}")
            print(f"    path: {item.get('path', '<missing path>')}")
            print(f"    capture: {item.get('capture_command', '<missing capture command>')}")
            print(f"    validate: {item.get('validation_command', '<missing validation command>')}")
            for problem in problems:
                print(f"    blocker: {problem}")
    if errors:
        print("software BSP evidence status failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    return 2 if blocked else 0


def quote_env_assignment(name: str, value: str) -> str:
    return f"{name}={shlex.quote(value)}"


def render_capture_command(item: dict, args: argparse.Namespace) -> tuple[str, list[str]]:
    rel = item["path"]
    missing: list[str] = []

    def require_arg(attr: str, label: str) -> str:
        value = getattr(args, attr)
        if not value:
            missing.append(label)
            return f"<{label}>"
        return value

    if rel.startswith("docs/evidence/buildroot/"):
        buildroot = require_arg("buildroot", "--buildroot")
        if rel.endswith("openphone_hello_defconfig.log"):
            return (
                f"sw/buildroot/scripts/capture-buildroot-evidence.sh {shlex.quote(buildroot)} defconfig",
                missing,
            )
        if rel.endswith("openphone_hello_image_manifest.txt"):
            return (
                f"sw/buildroot/scripts/capture-buildroot-evidence.sh {shlex.quote(buildroot)} image-manifest",
                missing,
            )
        smoke = args.buildroot_smoke_cmd or (
            f"ssh {args.target_host} /usr/bin/hello-mmio-smoke" if args.target_host else ""
        )
        if not smoke:
            missing.append("--buildroot-smoke-cmd or --target-host")
            smoke = "<buildroot smoke command>"
        return (
            f"{quote_env_assignment('HELLO_SMOKE_CMD', smoke)} "
            f"sw/buildroot/scripts/capture-buildroot-evidence.sh {shlex.quote(buildroot)} smoke",
            missing,
        )

    if (
        rel.startswith("docs/evidence/linux/openphone_hello_")
        or rel == "docs/evidence/linux/hello-mmio-smoke.log"
    ):
        linux = require_arg("linux", "--linux")
        prefix = ""
        if args.cross_compile:
            prefix += f"{quote_env_assignment('CROSS_COMPILE', args.cross_compile)} "
        if args.jobs:
            prefix += f"{quote_env_assignment('JOBS', str(args.jobs))} "
        if rel.endswith("openphone_hello_kernel_build.log"):
            return (
                f"{prefix}sw/linux/scripts/capture-linux-bsp-evidence.sh {shlex.quote(linux)} kernel-build",
                missing,
            )
        if rel.endswith("openphone_hello_dtb_check.log"):
            return (
                f"{prefix}sw/linux/scripts/capture-linux-bsp-evidence.sh {shlex.quote(linux)} dtb-check",
                missing,
            )
        smoke = args.linux_smoke_cmd or (
            f"ssh {args.target_host} /tmp/hello-mmio-smoke" if args.target_host else ""
        )
        if not smoke:
            missing.append("--linux-smoke-cmd or --target-host")
            smoke = "<linux smoke command>"
        return (
            f"{prefix}{quote_env_assignment('HELLO_SMOKE_CMD', smoke)} "
            f"sw/linux/scripts/capture-linux-bsp-evidence.sh {shlex.quote(linux)} smoke",
            missing,
        )

    if rel.startswith("docs/evidence/linux/opensbi_"):
        opensbi = require_arg("opensbi", "--opensbi")
        if rel.endswith("opensbi_openphone_build.log"):
            command = args.opensbi_build_cmd or "make PLATFORM=generic FW_DYNAMIC=y"
            return (
                f"{quote_env_assignment('OPENPHONE_OPENSBI_CMD', command)} "
                f"sw/opensbi/capture-opensbi-evidence.sh {shlex.quote(opensbi)} build",
                missing,
            )
        handoff = args.opensbi_handoff_cmd
        if not handoff:
            missing.append("--opensbi-handoff-cmd")
            handoff = "<OpenSBI handoff boot command>"
        return (
            f"{quote_env_assignment('OPENPHONE_OPENSBI_HANDOFF_CMD', handoff)} "
            f"sw/opensbi/capture-opensbi-evidence.sh {shlex.quote(opensbi)} handoff",
            missing,
        )

    if rel.startswith("docs/evidence/linux/u_boot_"):
        uboot = require_arg("u_boot", "--u-boot")
        if rel.endswith("u_boot_openphone_build.log"):
            command = args.uboot_build_cmd
            if not command:
                missing.append("--uboot-build-cmd")
                command = "<U-Boot build command>"
            return (
                f"{quote_env_assignment('OPENPHONE_UBOOT_CMD', command)} "
                f"sw/u-boot/capture-u-boot-evidence.sh {shlex.quote(uboot)} build",
                missing,
            )
        command = args.uboot_boot_cmd
        if not command:
            missing.append("--uboot-boot-cmd")
            command = "<OpenSBI-to-U-Boot boot command>"
        return (
            f"{quote_env_assignment('OPENPHONE_UBOOT_BOOT_CMD', command)} "
            f"sw/u-boot/capture-u-boot-evidence.sh {shlex.quote(uboot)} boot-chain",
            missing,
        )

    if rel.startswith("docs/evidence/android/"):
        aosp = require_arg("aosp", "--aosp")
        mode_by_path = {
            "docs/evidence/android/openphone_ai_soc_lunch.log": "lunch",
            "docs/evidence/android/openphone_ai_soc_vendorimage.log": "vendorimage",
            "docs/evidence/android/openphone_ai_soc_checkvintf.log": "checkvintf",
            "docs/evidence/android/cuttlefish_riscv64_boot.log": "cuttlefish-boot",
            "docs/evidence/android/cts_virtual_device_subset.log": "cts-subset",
            "docs/evidence/android/vts_virtual_device_subset.log": "vts-subset",
        }
        prefix = (
            f"{quote_env_assignment('AOSP_SHELL', args.aosp_shell)} " if args.aosp_shell else ""
        )
        return (
            f"{prefix}sw/aosp-device/capture-aosp-evidence.sh {shlex.quote(aosp)} {mode_by_path[rel]}",
            missing,
        )

    return item.get("capture_command", "<missing capture command>"), [f"no renderer for {rel}"]


def print_capture_plan(args: argparse.Namespace) -> int:
    errors: list[str] = []
    manifest = load_evidence_manifest(errors)
    if errors:
        print("software BSP evidence manifest invalid:")
        for error in errors:
            print(f"  - {error}")
        return 1

    missing_inputs: list[str] = []
    for name in target_names_from_arg(args.target):
        print(f"{name}:")
        for item in evidence_items_for(name, manifest, errors):
            rendered, missing = render_capture_command(item, args)
            missing_inputs.extend(f"{item['path']}: {value}" for value in missing)
            print(f"  # {item.get('artifact', '<missing artifact>')}")
            print(f"  # writes {item.get('path', '<missing path>')}")
            print(f"  {rendered}")
    if errors:
        print("software BSP capture plan failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    if missing_inputs:
        print("missing inputs for exact capture commands:")
        for missing_input in missing_inputs:
            print(f"  - {missing_input}")
        return 2
    return 0


def parse_helper(argv: list[str]) -> argparse.Namespace | None:
    if not argv or argv[0] not in {"status", "capture-plan"}:
        return None
    if argv[0] == "status":
        parser = argparse.ArgumentParser(
            description="Report software BSP external evidence status."
        )
        parser.add_argument("command", choices=["status"])
        parser.add_argument("target", choices=[*TARGETS.keys(), "all"], nargs="?", default="all")
        return parser.parse_args(argv)

    parser = argparse.ArgumentParser(
        description="Print exact external software BSP capture commands."
    )
    parser.add_argument("command", choices=["capture-plan"])
    parser.add_argument("target", choices=[*TARGETS.keys(), "all"], nargs="?", default="all")
    parser.add_argument("--buildroot", help="External Buildroot checkout path.")
    parser.add_argument("--linux", help="External Linux checkout path.")
    parser.add_argument("--opensbi", help="External OpenSBI checkout path.")
    parser.add_argument("--u-boot", dest="u_boot", help="External U-Boot checkout path.")
    parser.add_argument("--aosp", help="External AOSP checkout path.")
    parser.add_argument(
        "--target-host", help="SSH target used by Buildroot and Linux smoke commands."
    )
    parser.add_argument("--buildroot-smoke-cmd", help="Exact Buildroot target MMIO smoke command.")
    parser.add_argument("--linux-smoke-cmd", help="Exact Linux target MMIO smoke command.")
    parser.add_argument("--opensbi-build-cmd", help="Exact OpenSBI build command.")
    parser.add_argument(
        "--opensbi-handoff-cmd", help="Exact OpenSBI fw_dynamic handoff boot command."
    )
    parser.add_argument("--uboot-build-cmd", help="Exact U-Boot build command.")
    parser.add_argument("--uboot-boot-cmd", help="Exact OpenSBI-to-U-Boot boot-chain command.")
    parser.add_argument("--cross-compile", help="Linux CROSS_COMPILE prefix.")
    parser.add_argument("--jobs", type=int, help="Linux build parallelism.")
    parser.add_argument("--aosp-shell", help="Shell used to source AOSP envsetup.sh.")
    return parser.parse_args(argv)


def check_target(name: str) -> tuple[list[str], list[str]]:
    spec = TARGETS[name]
    errors: list[str] = []
    blockers: list[str] = []
    check_contract(errors)
    manifest = load_evidence_manifest(errors)

    readme = spec["readme"]
    if not readme.is_file():
        errors.append(f"{readme.relative_to(ROOT)} is missing")
        return errors, blockers

    text = readme.read_text(errors="ignore")
    if "placeholder-only target" in text.lower():
        errors.append(f"{readme.relative_to(ROOT)} still describes a placeholder-only target")
    if "sw/platform/hello_platform_contract.json" not in text:
        errors.append(
            f"{readme.relative_to(ROOT)} does not reference the central platform contract"
        )

    missing = [path for path in spec["required"] if not (ROOT / path).exists()]
    if missing:
        errors.append(
            f"{name} BSP is not implemented; missing required artifacts: " + ", ".join(missing)
        )

    present_text = "\n".join(
        path.read_text(errors="ignore")
        for path in (ROOT / spec_path for spec_path in spec["required"])
        if path.is_file()
    )
    if present_text:
        missing_terms = [term for term in spec["contract_terms"] if term not in present_text]
        if missing_terms:
            errors.append(
                f"{name} BSP artifacts do not expose expected contract terms: "
                + ", ".join(missing_terms)
            )

    if name == "aosp":
        check_aosp_product_glue(errors)
        check_aosp_evidence_manifest(errors)

    evidence_items = evidence_items_for(name, manifest, errors) if manifest else []
    manifest_paths = [item.get("path") for item in evidence_items]
    missing_manifest_paths = [path for path in spec["evidence"] if path not in manifest_paths]
    if missing_manifest_paths:
        errors.append(
            f"{name} evidence manifest does not enumerate required evidence paths: "
            + ", ".join(missing_manifest_paths)
        )
    evidence_problems = []
    for item in evidence_items:
        evidence_problems.extend(validate_evidence_file(item))
    if name == "aosp":
        check_aosp_forbidden_claims(evidence_items, evidence_problems)
    if evidence_problems:
        blockers.append(
            f"{name} BSP BLOCKED: evidence for {spec['evidence_note']} is incomplete or invalid"
        )
        blockers.extend(evidence_problems)

    return errors, blockers


def main() -> int:
    helper_args = parse_helper(sys.argv[1:])
    if helper_args:
        if helper_args.command == "status":
            return print_status(helper_args.target)
        if helper_args.command == "capture-plan":
            return print_capture_plan(helper_args)

    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=[*TARGETS.keys(), "all"])
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help="Check only repo-local scaffold files and ignore external build/boot evidence.",
    )
    parser.add_argument(
        "--require-evidence",
        action="store_true",
        help="Return nonzero when external build/boot evidence logs are missing.",
    )
    parser.add_argument(
        "--evidence-plan",
        action="store_true",
        help="Print manifest capture commands, validation commands, and required markers.",
    )
    args = parser.parse_args()

    names = target_names_from_arg(args.target)
    if args.evidence_plan:
        return print_evidence_plan(names)

    failed = False
    for name in names:
        errors, blockers = check_target(name)
        scaffold_name = TARGETS[name].get("scaffold_audit", name)
        scaffold = subprocess.run(
            [sys.executable, "sw/check_bsp_scaffolds.py", scaffold_name],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if scaffold.stdout:
            print(scaffold.stdout, end="")
        if scaffold.stderr:
            print(scaffold.stderr, end="", file=sys.stderr)
        if scaffold.returncode:
            errors.append(f"{scaffold_name} scaffold audit failed")
        evidence_required = args.require_evidence and not args.scaffold_only
        if errors or (blockers and evidence_required):
            failed = True
            print(f"{name} BSP check failed:")
            for error in errors:
                print(f"  - {error}")
            if evidence_required:
                for blocker in blockers:
                    print(f"  - {blocker}")
        else:
            print(f"{name} BSP check passed.")
        if blockers:
            print(f"{name} BSP external evidence blocked:")
            for blocker in blockers:
                print(f"  - {blocker}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
