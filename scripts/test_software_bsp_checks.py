#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts/check_software_bsp.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_software_bsp_under_test", CHECKER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_log_parser_rejects_placeholder_failure() -> None:
    checker = load_checker()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = root / "docs/evidence/android/openphone_ai_soc_lunch.log"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            "EXTERNAL_TREE=/external/aosp\n"
            "COMMAND=lunch openphone_ai_soc-userdebug\n"
            "START_UTC=2026-05-17T00:00:00Z\n"
            "END_UTC=2026-05-17T00:01:00Z\n"
            "RESULT=pass\n"
            "TARGET_PRODUCT=openphone_ai_soc\n"
            "TARGET_ARCH=riscv64\n"
            "placeholder transcript\n"
        )
        manifest = root / "docs/android/bsp-log-evidence-manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "claim_boundary": "expected_future_log_markers_only_not_boot_evidence",
                    "logs": {
                        "docs/evidence/android/openphone_ai_soc_lunch.log": {
                            "producer_command": "lunch openphone_ai_soc-userdebug",
                            "capture_hint": "capture real lunch output with provenance header",
                            "required_metadata": ["EXTERNAL_TREE=", "COMMAND=", "START_UTC=", "END_UTC=", "RESULT="],
                            "required_any": ["TARGET_PRODUCT=openphone_ai_soc"],
                            "required_all": ["TARGET_ARCH=riscv64"],
                            "forbidden_any": ["placeholder"],
                        }
                    },
                }
            )
        )
        checker.ROOT = root
        checker.LOG_EVIDENCE_MANIFEST = manifest
        errors: list[str] = []
        checker.check_log_evidence("docs/evidence/android/openphone_ai_soc_lunch.log", errors)
        assert any("forbidden" in error for error in errors), errors


def test_log_parser_requires_provenance_metadata() -> None:
    checker = load_checker()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = root / "docs/evidence/linux/openphone_hello_kernel_build.log"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            "CONFIG_OPENPHONE_HELLO_NPU=y\n"
            "CONFIG_OPENPHONE_HELLO_DMA=y\n"
            "Kernel: arch/riscv/boot/Image is ready\n"
        )
        manifest = root / "docs/android/bsp-log-evidence-manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "claim_boundary": "expected_future_log_markers_only_not_boot_evidence",
                    "logs": {
                        "docs/evidence/linux/openphone_hello_kernel_build.log": {
                            "producer_command": "make Image dtbs modules",
                            "capture_hint": "capture real kernel output with provenance header",
                            "required_metadata": ["EXTERNAL_TREE=", "COMMAND=", "START_UTC=", "END_UTC=", "RESULT="],
                            "required_any": ["Kernel: arch/riscv/boot/Image is ready"],
                            "required_all": ["CONFIG_OPENPHONE_HELLO_NPU", "CONFIG_OPENPHONE_HELLO_DMA"],
                            "forbidden_any": ["placeholder"],
                        }
                    },
                }
            )
        )
        checker.ROOT = root
        checker.LOG_EVIDENCE_MANIFEST = manifest
        errors: list[str] = []
        checker.check_log_evidence("docs/evidence/linux/openphone_hello_kernel_build.log", errors)
        assert any("provenance" in error for error in errors), errors


def test_aosp_product_glue_rejects_hal_packages_without_sources() -> None:
    checker = load_checker()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        device = root / "sw/aosp-device/device/openphone/openphone_ai_soc"
        device.mkdir(parents=True)
        (device / "AndroidProducts.mk").write_text(
            "COMMON_LUNCH_CHOICES := openphone_ai_soc-userdebug\n"
        )
        (device / "BoardConfig.mk").write_text(
            "TARGET_ARCH := riscv64\n"
            "BOARD_VENDOR_SEPOLICY_DIRS += device/openphone/openphone_ai_soc/sepolicy\n"
            "OPENPHONE_KERNEL_CONFIG_FRAGMENT := kernel/openphone_ai_soc.fragment\n"
            "OPENPHONE_DTS := dts/openphone-hello-android.dts\n"
        )
        (device / "manifest.xml").write_text("<manifest><hal></hal></manifest>\n")
        (device / "device.mk").write_text("PRODUCT_PACKAGES += hello_npu.default\n")
        checker.ROOT = root
        errors: list[str] = []
        checker.check_aosp_product_glue(errors)
        assert any("must not list HAL packages" in error for error in errors), errors


def test_aosp_product_glue_rejects_active_vintf_hal_without_sources() -> None:
    checker = load_checker()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        device = root / "sw/aosp-device/device/openphone/openphone_ai_soc"
        device.mkdir(parents=True)
        (device / "AndroidProducts.mk").write_text(
            "COMMON_LUNCH_CHOICES := openphone_ai_soc-userdebug\n"
        )
        (device / "BoardConfig.mk").write_text(
            "TARGET_ARCH := riscv64\n"
            "BOARD_VENDOR_SEPOLICY_DIRS += device/openphone/openphone_ai_soc/sepolicy\n"
            "OPENPHONE_KERNEL_CONFIG_FRAGMENT := kernel/openphone_ai_soc.fragment\n"
            "OPENPHONE_DTS := dts/openphone-hello-android.dts\n"
        )
        (device / "manifest.xml").write_text(
            "<manifest>"
            "<!-- hello_npu hwcomposer.openphone_ai_soc -->"
            "<hal><name>vendor.openphone.hello_npu</name></hal>"
            "</manifest>\n"
        )
        (device / "device.mk").write_text("# no packages\n")
        checker.ROOT = root
        errors: list[str] = []
        checker.check_aosp_product_glue(errors)
        assert any("must not declare active HAL entries" in error for error in errors), errors


def main() -> int:
    test_log_parser_rejects_placeholder_failure()
    test_log_parser_requires_provenance_metadata()
    test_aosp_product_glue_rejects_hal_packages_without_sources()
    test_aosp_product_glue_rejects_active_vintf_hal_without_sources()
    print("software BSP parser tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
