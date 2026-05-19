#!/usr/bin/env python3
"""Generate liveness-only simulator metrics from the QEMU smoke artifact.

This file intentionally does not estimate phone performance. The benchmark
harness requires numeric simulator fields so the report is machine-parseable;
for the current qemu-virt smoke, those fields are zero until an architecture
simulator exports real cycle, frequency, and IPC measurements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QEMU_LOG = ROOT / "build/reports/qemu_smoke.log"
DEFAULT_OUT = ROOT / "benchmarks/results/simulator-arch-metrics.json"
BANNER = "openagent e1 qemu"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qemu-log", type=Path, default=DEFAULT_QEMU_LOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    qemu_log = resolve(args.qemu_log)
    out = resolve(args.out)
    if not qemu_log.is_file():
        raise SystemExit(f"missing qemu smoke log: {qemu_log.relative_to(ROOT)}")

    text = qemu_log.read_text(errors="ignore")
    if BANNER not in text:
        raise SystemExit(f"qemu smoke log does not contain required banner: {BANNER}")

    data = {
        "schema": "openagent.simulator_arch_metrics.v1",
        "evidence_class": "qemu_virt_liveness_only",
        "claim_boundary": "not_performance_evidence",
        "calibration_status": "uncalibrated",
        "benchmark_success_allowed": False,
        "source_log": display_path(qemu_log),
        "observed_banner": BANNER,
        "target_cycles": 0,
        "simulated_frequency_hz": 0,
        "ipc": 0,
        "notes": [
            "QEMU smoke confirms firmware liveness only.",
            "Cycle, frequency, and IPC remain zero until gem5, RTL, FPGA, or silicon metrics exist.",
            "Do not compare this artifact with phone-class benchmark results.",
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {display_path(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
