#!/usr/bin/env python3
"""Run type and schema-adjacent checks for source files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(name: str, cmd: list[str], *, optional: bool = False) -> bool:
    if shutil.which(cmd[0]) is None:
        status = "BLOCK" if optional else "FAIL"
        print(f"{status}: {name}: missing tool {cmd[0]}")
        return optional
    print(f"RUN: {name}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"PASS: {name}")
        return True
    print(f"FAIL: {name}: exit {result.returncode}")
    return False


def main() -> int:
    ok = True
    ok &= run("python mypy", ["mypy", "--config-file", "pyproject.toml"])
    ok &= run(
        "python compileall",
        [
            "python3",
            "-m",
            "compileall",
            "-q",
            "benchmarks",
            "compiler",
            "package",
            "scripts",
            "sw",
            "verify",
            "fw",
        ],
    )
    ok &= run("platform contract schema", ["python3", "scripts/check_platform_contract.py"])
    ok &= run("project plan schema", ["python3", "scripts/check_project_plan.py"])
    ok &= run("software BSP schema", ["python3", "scripts/check_software_bsp.py", "all"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
