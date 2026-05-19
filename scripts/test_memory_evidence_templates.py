#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import check_memory_evidence_templates as templates


class MemoryEvidenceTemplateTest(unittest.TestCase):
    def test_template_checker_passes_without_real_reports(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_memory_evidence_templates.py"],
            cwd=templates.ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("template_only", templates.TEMPLATE.read_text())
        self.assertIn("placeholder rejection is armed", result.stdout)

    def test_placeholder_real_report_is_rejected(self) -> None:
        report = json.loads(templates.TEMPLATE.read_text())["report"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "placeholder-report.json"
            path.write_text(json.dumps(report), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/check_memory_evidence_templates.py",
                    "--report",
                    str(path),
                ],
                cwd=templates.ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contains placeholders", result.stdout)


if __name__ == "__main__":
    unittest.main()
