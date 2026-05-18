#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_software_bsp  # noqa: E402


class SoftwareBspEvidenceTest(unittest.TestCase):
    def test_manifest_enumerates_all_checker_evidence_paths(self) -> None:
        manifest = json.loads(check_software_bsp.EVIDENCE_MANIFEST.read_text())
        self.assertEqual(manifest["claim_boundary"], "external_transcripts_only")

        for target, spec in check_software_bsp.TARGETS.items():
            with self.subTest(target=target):
                manifest_paths = {item["path"] for item in manifest["targets"][target]["evidence"]}
                self.assertEqual(set(spec["evidence"]), manifest_paths)

    def test_android_manifest_does_not_claim_compatibility(self) -> None:
        manifest = json.loads(check_software_bsp.AOSP_EVIDENCE_MANIFEST.read_text())
        self.assertEqual(
            manifest["claim_boundary"],
            "android_external_logs_only_not_boot_or_compatibility_evidence",
        )
        self.assertEqual(
            manifest["compatibility_claim"],
            "none_without_full_external_compatibility_evidence",
        )

        paths = {item["path"] for item in manifest["evidence"]}
        self.assertIn("docs/evidence/android/openphone_ai_soc_cts_vts_plan.log", paths)
        self.assertIn("docs/evidence/android/cuttlefish_riscv64_smoke.log", paths)
        self.assertIn("docs/evidence/android/qemu_riscv64_smoke.log", paths)
        self.assertIn("docs/evidence/android/renode_hello_soc_smoke.log", paths)
        claims = "\n".join(item["claim"] for item in manifest["evidence"])
        self.assertNotIn("CDD compliant", claims)
        self.assertNotIn("full CTS pass", claims)
        self.assertNotIn("full VTS pass", claims)

        by_path = {item["path"]: item for item in manifest["evidence"]}
        for path in check_software_bsp.AOSP_REFERENCE_ONLY_PATHS:
            self.assertEqual(
                by_path[path]["claim_boundary"],
                check_software_bsp.AOSP_VIRTUAL_DEVICE_BOUNDARY,
            )
            self.assertIn("reference", by_path[path]["claim"].lower())

    def test_scaffold_only_passes_while_listing_missing_external_logs(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_software_bsp.py", "all", "--scaffold-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "missing docs/evidence/buildroot/openphone_hello_defconfig.log", result.stdout
        )
        self.assertIn(
            "missing docs/evidence/android/openphone_ai_soc_sepolicy_build.log",
            result.stdout,
        )
        self.assertIn("missing docs/evidence/android/qemu_riscv64_smoke.log", result.stdout)
        self.assertNotIn("missing docs/evidence/linux/opensbi_openphone_build.log", result.stdout)
        self.assertNotIn("missing docs/evidence/linux/u_boot_openphone_build.log", result.stdout)

    def test_require_evidence_fails_closed_on_missing_external_logs(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_software_bsp.py", "all", "--require-evidence"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("buildroot BSP check failed", result.stdout)
        self.assertIn("linux BSP check failed", result.stdout)
        self.assertIn("aosp BSP check failed", result.stdout)
        self.assertNotIn("opensbi BSP check failed", result.stdout)
        self.assertNotIn("u-boot BSP check failed", result.stdout)

    def test_status_helper_reports_missing_external_logs(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_software_bsp.py", "status", "buildroot"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[MISSING] Buildroot defconfig transcript", result.stdout)
        self.assertIn("capture:", result.stdout)
        self.assertIn("validate:", result.stdout)

    def test_capture_plan_renders_exact_buildroot_commands(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/check_software_bsp.py",
                "capture-plan",
                "buildroot",
                "--buildroot",
                "/external/buildroot",
                "--target-host",
                "root@openphone-target",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "sw/buildroot/scripts/capture-buildroot-evidence.sh /external/buildroot defconfig",
            result.stdout,
        )
        self.assertIn(
            "HELLO_SMOKE_CMD='ssh root@openphone-target /usr/bin/hello-mmio-smoke'",
            result.stdout,
        )

    def test_placeholder_or_failed_log_cannot_pass_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            evidence = temp_root / "docs/evidence/linux/fake.log"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                "\n".join(
                    [
                        "openphone-evidence: target=linux artifact=openphone_hello_kernel_build",
                        "openphone-evidence: command=make ARCH=riscv Image",
                        "openphone-evidence: started_utc=2026-05-17T00:00:00Z",
                        "CONFIG_OPENPHONE_HELLO=y",
                        "placeholder output",
                        "openphone-evidence: status=FAIL rc=1",
                        "openphone-evidence: ended_utc=2026-05-17T00:00:01Z",
                    ]
                )
            )
            item = {
                "path": "docs/evidence/linux/fake.log",
                "min_bytes": 80,
                "capture_command": "fake",
                "required_strings": [
                    "openphone-evidence: target=linux artifact=openphone_hello_kernel_build",
                    "CONFIG_OPENPHONE_HELLO",
                    "openphone-evidence: status=PASS",
                ],
            }

            with mock.patch.object(check_software_bsp, "ROOT", temp_root):
                problems = check_software_bsp.validate_evidence_file(item)

        joined = "\n".join(problems)
        self.assertIn("reports non-PASS evidence status: FAIL", joined)
        self.assertIn("contains forbidden placeholder/failure markers", joined)
        self.assertIn("missing required transcript markers", joined)

    def test_reference_only_android_logs_require_explicit_boundary_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            evidence = temp_root / "docs/evidence/android/cuttlefish_riscv64_boot.log"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                "\n".join(
                    [
                        "openphone-evidence: target=aosp artifact=cuttlefish_riscv64_boot",
                        "openphone-evidence: command=launch_cvd",
                        "openphone-evidence: started_utc=2026-05-17T00:00:00Z",
                        "launch_cvd",
                        "adb shell",
                        "ro.product.cpu.abi=riscv64",
                        "sys.boot_completed=1",
                        "openphone-evidence: ended_utc=2026-05-17T00:00:01Z",
                        "openphone-evidence: status=PASS",
                    ]
                )
            )
            item = {
                "path": "docs/evidence/android/cuttlefish_riscv64_boot.log",
                "claim_boundary": check_software_bsp.AOSP_REFERENCE_ONLY_BOUNDARY,
                "min_bytes": 80,
                "capture_command": "fake",
                "required_strings": [
                    "openphone-evidence: target=aosp artifact=cuttlefish_riscv64_boot",
                    "launch_cvd",
                    "adb shell",
                    "ro.product.cpu.abi=riscv64",
                    "sys.boot_completed=1",
                    "openphone-evidence: status=PASS",
                ],
            }

            with mock.patch.object(check_software_bsp, "ROOT", temp_root):
                problems = check_software_bsp.validate_evidence_file(item)

        self.assertIn("missing reference-only claim boundary marker", "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
