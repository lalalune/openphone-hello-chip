#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"
EVIDENCE_MANIFEST = ROOT / "docs/evidence/software-bsp-evidence-manifest.json"
AOSP_EVIDENCE_MANIFEST = ROOT / "sw/aosp-device/evidence_manifest.json"

DEFAULT_FORBIDDEN_EVIDENCE_TERMS = [
    "placeholder",
    "template only",
    "sample only",
    "not real evidence",
    "todo",
    "openphone-evidence: template=true",
    "openphone-evidence: status=FAIL",
    "openphone-evidence: status=BLOCKED",
]


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
    if not EVIDENCE_MANIFEST.is_file():
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} is missing")
        return {}
    try:
        data = json.loads(EVIDENCE_MANIFEST.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} is invalid JSON: {exc}")
        return {}
    if data.get("schema_version") != 1:
        errors.append(f"{EVIDENCE_MANIFEST.relative_to(ROOT)} must have schema_version=1")
    if data.get("claim_boundary") != "external_transcripts_only":
        errors.append(
            f"{EVIDENCE_MANIFEST.relative_to(ROOT)} must use claim_boundary=external_transcripts_only"
        )
    return data


def validate_manifest_item(target: str, item: dict, errors: list[str]) -> None:
    path = item.get("path")
    if not isinstance(path, str) or not path.startswith("docs/evidence/"):
        errors.append(f"{target} evidence item has invalid repo-relative path: {path!r}")
    elif path not in TARGETS[target]["evidence"]:
        errors.append(
            f"{target} evidence item path is not listed in checker target evidence: {path}"
        )
    for key in ("artifact", "capture_command", "required_strings"):
        if key not in item:
            errors.append(f"{target} evidence item {path or '<unknown>'} missing {key}")
    if not isinstance(item.get("required_strings", []), list):
        errors.append(
            f"{target} evidence item {path or '<unknown>'} required_strings must be a list"
        )
    if not isinstance(item.get("at_least_one", []), list):
        errors.append(f"{target} evidence item {path or '<unknown>'} at_least_one must be a list")


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
    if not AOSP_EVIDENCE_MANIFEST.is_file():
        errors.append(f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} is missing")
        return {}
    try:
        data = json.loads(AOSP_EVIDENCE_MANIFEST.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"{AOSP_EVIDENCE_MANIFEST.relative_to(ROOT)} is invalid JSON: {exc}")
        return {}
    return data


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
    args = parser.parse_args()

    names = TARGETS.keys() if args.target == "all" else [args.target]
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
