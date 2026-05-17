#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "build/reports/sim_ladder.json"

LADDER = [
    {
        "name": "cocotb_top",
        "command": ["make", "cocotb"],
        "required_artifacts": ["build/reports/cocotb/hello_chip_top_test_hello_chip.xml"],
    },
    {
        "name": "cocotb_contract",
        "command": ["make", "cocotb-contract"],
        "required_artifacts": [
            "build/reports/cocotb/hello_linux_soc_contract_test_cpu_mem_intc_contract.xml"
        ],
    },
    {
        "name": "cocotb_cpu",
        "command": ["make", "cocotb-cpu"],
        "required_artifacts": [
            "build/reports/cocotb/hello_tiny_cpu_contract_tb_test_tiny_cpu_execution.xml"
        ],
    },
    {
        "name": "verilator_smoke",
        "command": ["make", "verilator"],
        "required_artifacts": ["build/verilator/Vhello_chip_top"],
    },
]


def run_step(step: dict[str, Any]) -> dict[str, Any]:
    command = step["command"]
    assert isinstance(command, list)
    start = time.time()
    result = subprocess.run(
        command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    elapsed = round(time.time() - start, 3)
    artifacts = step.get("required_artifacts", [])
    if not isinstance(artifacts, list):
        artifacts = []
    missing = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, str) and not (ROOT / artifact).exists()
    ]
    status = "pass" if result.returncode == 0 and not missing else "fail"
    return {
        "name": step["name"],
        "command": command,
        "status": status,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "required_artifacts": artifacts,
        "missing_artifacts": missing,
        "log_tail": result.stdout.splitlines()[-40:],
    }


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for step in LADDER:
        result = run_step(step)
        results.append(result)
        if result["status"] != "pass":
            break

    manifest = {
        "schema": "openphone.sim_ladder.v1",
        "status": "pass"
        if all(item["status"] == "pass" for item in results) and len(results) == len(LADDER)
        else "fail",
        "results": results,
    }
    tmp = REPORT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    tmp.replace(REPORT)

    if manifest["status"] != "pass":
        print(f"Simulation ladder failed; wrote {REPORT.relative_to(ROOT)}")
        for item in results:
            print(f"  - {item['name']}: {item['status']}")
            if item["status"] != "pass":
                log_tail = item.get("log_tail", [])
                if not isinstance(log_tail, list):
                    log_tail = []
                for line in log_tail[-10:]:
                    print(f"    {line}")
                break
        return 1

    print(f"Simulation ladder passed; wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
