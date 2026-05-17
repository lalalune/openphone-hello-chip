#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"
ARTIFACT_MANIFEST = ROOT / "docs/android/bsp-artifact-manifest.json"
LOG_EVIDENCE_MANIFEST = ROOT / "docs/android/bsp-log-evidence-manifest.json"
BOOT_TRANSCRIPT_SCHEMA = ROOT / "docs/android/boot-transcript.schema.json"
DEFAULT_EVIDENCE_METADATA = ["EXTERNAL_TREE=", "COMMAND=", "START_UTC=", "END_UTC=", "RESULT="]
ANDROID_COMPAT_METADATA = [
    "EXTERNAL_TREE=",
    "COMMAND=",
    "START_UTC=",
    "END_UTC=",
    "RESULT=",
    "COMPATIBILITY_CLAIM=none",
]

TARGETS: dict[str, dict[str, Any]] = {
    "buildroot": {
        "readme": ROOT / "docs/sw/buildroot/README.md",
        "required": [
            "docs/android/bsp-artifact-manifest.json",
            "docs/android/bsp-log-evidence-manifest.json",
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
            "docs/android/bsp-artifact-manifest.json",
            "docs/android/bsp-log-evidence-manifest.json",
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
    "aosp": {
        "readme": ROOT / "docs/sw/aosp-device/README.md",
        "required": [
            "docs/android/bsp-artifact-manifest.json",
            "docs/android/bsp-log-evidence-manifest.json",
            "sw/aosp-device/import-aosp-device.sh",
            "sw/aosp-device/manifests/openphone-ai-soc-local.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
            "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
            "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
            "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
            "docs/sw/aosp-device/device/openphone/openphone_ai_soc/hal/README.md",
            "docs/android/boot-transcript.schema.json",
        ],
        "contract_terms": ["openphone_ai_soc", "hello_npu", "hwcomposer"],
        "evidence": [
            "docs/evidence/android/openphone_ai_soc_lunch.log",
            "docs/evidence/android/openphone_ai_soc_vendorimage.log",
            "docs/evidence/android/openphone_ai_soc_checkvintf.log",
            "docs/evidence/android/openphone_ai_soc_sepolicy_build.log",
            "docs/evidence/android/openphone_ai_soc_selinux_neverallow.log",
            "docs/evidence/android/openphone_ai_soc_cts_vts_plan.log",
            "docs/evidence/android/cuttlefish_riscv64_smoke.log",
            "docs/evidence/android/qemu_riscv64_smoke.log",
            "docs/evidence/android/renode_hello_soc_smoke.log",
        ],
        "evidence_note": "external AOSP lunch/vendorimage/VINTF/SELinux/CTS-VTS intake logs plus virtual-device smoke transcripts",
    },
}


def load_json(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"{path.relative_to(ROOT)} is missing")
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
        return {}


def existing_repo_path(path: str) -> Path | None:
    direct = ROOT / path
    if direct.exists():
        return direct
    migrated = ROOT / "docs" / path
    if migrated.exists():
        return migrated
    return None


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


def check_artifact_manifest(name: str, errors: list[str]) -> None:
    manifest = load_json(ARTIFACT_MANIFEST, errors)
    if not manifest:
        return
    if manifest.get("claim_boundary") != "host_checkable_manifest_only_not_boot_evidence":
        errors.append(
            "docs/android/bsp-artifact-manifest.json must keep a non-boot-evidence claim boundary"
        )
    target = manifest.get("targets", {}).get(name)
    if not target:
        errors.append(f"docs/android/bsp-artifact-manifest.json missing target {name}")
        return
    required_repo_evidence = target.get("required_repo_evidence", [])
    expected = TARGETS[name]["evidence"]
    if sorted(required_repo_evidence) != sorted(expected):
        errors.append(
            f"{name} artifact manifest evidence list does not match check_software_bsp.py"
        )
    if not target.get("required_outputs"):
        errors.append(f"{name} artifact manifest must list external build outputs")
    if not target.get("external_tree"):
        errors.append(f"{name} artifact manifest must identify the external tree boundary")
    if not target.get("source_command"):
        errors.append(
            f"{name} artifact manifest must list the source command for evidence production"
        )
    if "boot" in target.get("minimum_claim_to_clear_block", "").lower() and name != "aosp":
        errors.append(f"{name} manifest must not imply Android boot evidence")


def check_log_evidence(path: str, errors: list[str], *, strict: bool = True) -> list[str]:
    problems: list[str] = []
    manifest = load_json(LOG_EVIDENCE_MANIFEST, errors)
    if not manifest:
        return problems
    if manifest.get("claim_boundary") != "expected_future_log_markers_only_not_boot_evidence":
        errors.append(
            "docs/android/bsp-log-evidence-manifest.json must keep a non-boot-evidence claim boundary"
        )
    spec = manifest.get("logs", {}).get(path)
    if not spec:
        errors.append(f"docs/android/bsp-log-evidence-manifest.json missing parser spec for {path}")
        return problems
    if not spec.get("producer_command"):
        errors.append(
            f"docs/android/bsp-log-evidence-manifest.json missing producer_command for {path}"
        )
    if not spec.get("required_metadata"):
        errors.append(
            f"docs/android/bsp-log-evidence-manifest.json missing required_metadata for {path}"
        )
    if not spec.get("capture_hint"):
        errors.append(
            f"docs/android/bsp-log-evidence-manifest.json missing capture_hint for {path}"
        )
    if not spec.get("claim_boundary"):
        errors.append(
            f"docs/android/bsp-log-evidence-manifest.json missing claim_boundary for {path}"
        )
    evidence_path = ROOT / path
    if not evidence_path.is_file():
        return problems
    text = evidence_path.read_text(errors="ignore")
    metadata = spec.get("required_metadata", DEFAULT_EVIDENCE_METADATA)
    missing_metadata = [term for term in metadata if term not in text]
    if missing_metadata:
        problems.append(
            f"{path} missing required evidence provenance fields: " + ", ".join(missing_metadata)
        )
    missing_all = [term for term in spec.get("required_all", []) if term not in text]
    if missing_all:
        problems.append(f"{path} missing required log markers: " + ", ".join(missing_all))
    any_terms = spec.get("required_any", [])
    if any_terms and not any(term in text for term in any_terms):
        problems.append(f"{path} missing one of required log markers: " + ", ".join(any_terms))
    forbidden_terms = [term for term in spec.get("forbidden_any", []) if term in text]
    if forbidden_terms:
        problems.append(
            f"{path} contains forbidden failure/placeholder markers: " + ", ".join(forbidden_terms)
        )
    forbidden_claims = [
        term for term in spec.get("forbidden_claims", []) if term.lower() in text.lower()
    ]
    if forbidden_claims:
        problems.append(
            f"{path} contains forbidden broad claim markers: " + ", ".join(forbidden_claims)
        )
    if strict:
        errors.extend(problems)
    return problems


def check_boot_transcript_schema(errors: list[str]) -> None:
    schema = load_json(BOOT_TRANSCRIPT_SCHEMA, errors)
    if not schema:
        return
    if schema.get("$id") != "openphone.android_virtual_device_smoke.schema.v1":
        errors.append("docs/android/boot-transcript.schema.json has unexpected $id")
    properties = schema.get("properties", {})
    environment = properties.get("environment", {})
    expected_envs = {"cuttlefish_riscv64", "qemu_riscv64", "renode_hello_soc"}
    if set(environment.get("enum", [])) != expected_envs:
        errors.append(
            "virtual-device smoke schema must enumerate Cuttlefish, QEMU, and Renode evidence environments"
        )
    boundary = properties.get("claim_boundary", {}).get("const")
    if boundary != "virtual_device_smoke_only_not_boot_or_compatibility_evidence":
        errors.append(
            "virtual-device smoke schema must keep a no-boot/no-compatibility claim boundary"
        )
    required = set(schema.get("required", []))
    for field in ["smoke_log_path", "required_markers", "forbidden_markers", "blockers"]:
        if field not in required:
            errors.append(f"virtual-device smoke schema missing required field {field}")


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
        for term in ["<manifest", "hello_npu", "hwcomposer.openphone_ai_soc"]:
            if term not in manifest_text:
                errors.append(f"AOSP VINTF manifest missing XML marker {term}")
        if "</manifest>" not in manifest_text and "/>" not in manifest_text:
            errors.append("AOSP VINTF manifest is missing closing </manifest> marker")
        active_text = "\n".join(
            line for line in manifest_text.splitlines() if not line.strip().startswith("<!--")
        )
        if "<hal" in active_text:
            errors.append(
                "AOSP VINTF manifest must not declare active HAL entries until source or prebuilts exist"
            )
    device = ROOT / "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk"
    device_text = device.read_text(errors="ignore") if device.is_file() else ""
    if "PRODUCT_PACKAGES +=" in device_text and (
        "hello_npu.default" in device_text or "hwcomposer.openphone_ai_soc" in device_text
    ):
        errors.append("AOSP device.mk must not list HAL packages until source or prebuilts exist")
    forbidden_feature_terms = [
        "android.hardware.camera",
        "android.hardware.audio",
        "android.hardware.bluetooth",
        "android.hardware.location.gps",
        "android.hardware.nfc",
        "android.hardware.telephony",
        "android.hardware.sensor",
        "handheld_core_hardware.xml",
        "android.software.cts",
        "gms",
    ]
    lowered_device_text = device_text.lower()
    for term in forbidden_feature_terms:
        if term in lowered_device_text:
            errors.append(
                f"AOSP device.mk must not declare Android product feature claim without evidence: {term}"
            )


def check_target(name: str) -> tuple[list[str], list[str]]:
    spec = TARGETS[name]
    errors: list[str] = []
    blockers: list[str] = []
    check_contract(errors)
    check_artifact_manifest(name, errors)

    readme = spec["readme"]
    if not readme.is_file():
        migrated_readme = ROOT / "docs" / readme.relative_to(ROOT)
        if migrated_readme.is_file():
            readme = migrated_readme
    if not readme.is_file():
        errors.append(f"{readme.relative_to(ROOT)} is missing")
        return errors, blockers

    text = readme.read_text(errors="ignore")
    if "placeholder" in text.lower():
        errors.append(f"{readme.relative_to(ROOT)} still describes a placeholder-only target")
    if "sw/platform/hello_platform_contract.json" not in text:
        errors.append(
            f"{readme.relative_to(ROOT)} does not reference the central platform contract"
        )

    missing = [path for path in spec["required"] if existing_repo_path(path) is None]
    if missing:
        errors.append(
            f"{name} BSP is not implemented; missing required artifacts: " + ", ".join(missing)
        )

    present_text = "\n".join(
        path.read_text(errors="ignore")
        for path in (existing_repo_path(spec_path) for spec_path in spec["required"])
        if path and path.is_file()
    )
    if present_text:
        missing_terms = [term for term in spec["contract_terms"] if term not in present_text]
        if missing_terms:
            errors.append(
                f"{name} BSP artifacts do not expose expected contract terms: "
                + ", ".join(missing_terms)
            )

    if name == "aosp":
        check_boot_transcript_schema(errors)
        check_aosp_product_glue(errors)

    missing_evidence = [path for path in spec.get("evidence", []) if not (ROOT / path).is_file()]
    for path in spec.get("evidence", []):
        blockers.extend(check_log_evidence(path, errors, strict=False))
    if missing_evidence:
        manifest = load_json(LOG_EVIDENCE_MANIFEST, [])
        missing_with_codes = []
        for path in missing_evidence:
            blocker_code = (
                manifest.get("logs", {})
                .get(path, {})
                .get("blocker_code", "missing_external_evidence")
            )
            missing_with_codes.append(f"{path}({blocker_code})")
        blockers.append(
            f"{name} BSP BLOCKED: missing evidence for {spec['evidence_note']}: "
            + ", ".join(missing_with_codes)
        )

    return errors, blockers


def target_report(name: str) -> dict:
    errors, blockers = check_target(name)
    missing_evidence = [
        path for path in TARGETS[name].get("evidence", []) if not (ROOT / path).is_file()
    ]
    manifest = load_json(LOG_EVIDENCE_MANIFEST, [])
    missing = []
    for path in missing_evidence:
        spec = manifest.get("logs", {}).get(path, {})
        missing.append(
            {
                "path": path,
                "blocker_code": spec.get("blocker_code", "missing_external_evidence"),
                "producer_command": spec.get("producer_command", ""),
                "claim_boundary": spec.get("claim_boundary", ""),
            }
        )
    return {
        "target": name,
        "scaffold_status": "FAIL" if errors else "PASS",
        "evidence_status": "BLOCKED" if missing_evidence else ("FAIL" if errors else "PASS"),
        "errors": errors,
        "blockers": blockers,
        "missing_evidence": missing,
    }


def print_evidence_plan(name: str) -> None:
    manifest_errors: list[str] = []
    manifest = load_json(LOG_EVIDENCE_MANIFEST, manifest_errors)
    spec = TARGETS[name]
    print(f"{name}: external evidence intake plan")
    print(f"  blocker: {spec['evidence_note']}")
    if manifest_errors:
        for error in manifest_errors:
            print(f"  error: {error}")
        return
    for path in spec.get("evidence", []):
        log_spec = manifest.get("logs", {}).get(path, {})
        print(f"  evidence: {path}")
        print(f"    producer: {log_spec.get('producer_command', 'MISSING')}")
        print(f"    claim boundary: {log_spec.get('claim_boundary', 'MISSING')}")
        print(f"    capture: {log_spec.get('capture_hint', 'MISSING')}")
        metadata = log_spec.get("required_metadata", DEFAULT_EVIDENCE_METADATA)
        print(f"    required metadata: {', '.join(metadata)}")
        if log_spec.get("required_all"):
            print(f"    required all: {', '.join(log_spec['required_all'])}")
        if log_spec.get("required_any"):
            print(f"    required any: {', '.join(log_spec['required_any'])}")
        if log_spec.get("forbidden_any"):
            print(f"    forbidden any: {', '.join(log_spec['forbidden_any'])}")


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
    parser.add_argument(
        "--evidence-plan",
        action="store_true",
        help="Print the expected external evidence files, commands, provenance fields, and parser markers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable scaffold/evidence status and blockers.",
    )
    args = parser.parse_args()

    names = TARGETS.keys() if args.target == "all" else [args.target]
    if args.json:
        reports = [target_report(name) for name in names]
        print(
            json.dumps(
                {"schema": "openphone.software_bsp_status.v1", "targets": reports},
                indent=2,
                sort_keys=True,
            )
        )
        evidence_required = args.require_evidence and not args.scaffold_only
        return (
            1
            if any(
                report["errors"] or (evidence_required and report["missing_evidence"])
                for report in reports
            )
            else 0
        )

    if args.evidence_plan:
        for name in names:
            print_evidence_plan(name)
        return 0

    failed = False
    for name in names:
        errors, blockers = check_target(name)
        scaffold = subprocess.run(
            [sys.executable, "sw/check_bsp_scaffolds.py", name],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if scaffold.stdout:
            print(scaffold.stdout, end="")
        if scaffold.stderr:
            print(scaffold.stderr, end="", file=sys.stderr)
        if scaffold.returncode:
            errors.append(f"{name} scaffold audit failed")
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
            if blockers:
                print(f"{name} BSP scaffold check passed; external evidence remains BLOCKED.")
            else:
                print(f"{name} BSP scaffold and evidence checks passed.")
        if blockers:
            print(f"{name} BSP external evidence blocked:")
            for blocker in blockers:
                print(f"  - {blocker}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
