#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path

import check_software_bsp

ROOT = Path(__file__).resolve().parents[1]


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
        self.assertEqual(manifest["claim_boundary"], "android_external_logs_only")
        self.assertEqual(manifest["compatibility_claim"], "none_without_cts_vts_logs")

        paths = {item["path"] for item in manifest["evidence"]}
        self.assertIn("docs/evidence/android/cts_virtual_device_subset.log", paths)
        self.assertIn("docs/evidence/android/vts_virtual_device_subset.log", paths)
        claims = "\n".join(item["claim"] for item in manifest["evidence"])
        self.assertNotIn("CDD compliant", claims)
        self.assertNotIn("full CTS pass", claims)
        self.assertNotIn("full VTS pass", claims)

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
        self.assertIn("missing docs/evidence/linux/opensbi_openphone_build.log", result.stdout)
        self.assertIn("missing docs/evidence/linux/u_boot_openphone_build.log", result.stdout)
        self.assertIn("missing docs/evidence/android/cts_virtual_device_subset.log", result.stdout)
        self.assertIn("missing docs/evidence/android/vts_virtual_device_subset.log", result.stdout)

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
        self.assertIn("opensbi BSP check failed", result.stdout)
        self.assertIn("u-boot BSP check failed", result.stdout)
        self.assertIn("aosp BSP check failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
