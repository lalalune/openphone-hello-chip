#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "benchmarks/sim/run_npu_scale_sim.py"


REQUIRED_KERNEL_KEYS = {
    "kernel",
    "target_cycles",
    "npu_cycles",
    "macs",
    "bytes_read",
    "bytes_written",
    "compute_cycles",
    "memory_cycles",
    "memory_wait_cycles",
    "stall_cycles",
    "utilization_percent",
    "modeled_frequency_hz",
    "throughput_ops_s",
    "observed_tops",
}
REQUIRED_PRECISIONS = {"INT4", "INT8", "FP16", "BF16", "FP8"}


def main() -> int:
    errors: list[str] = []
    if not SIM.is_file():
        return report([f"missing simulator: {SIM.relative_to(ROOT)}"])

    completed = subprocess.run(
        [sys.executable, str(SIM), "--config", "open_2028_first_50tops"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return report(["scale simulator command failed", completed.stderr.strip()])

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return report([f"scale simulator emitted invalid JSON: {exc}"])

    if data.get("schema") != "openphone.npu_scale_sim.v1":
        errors.append("scale simulator schema mismatch")
    config = data.get("config", {})
    if not isinstance(config, dict):
        errors.append("scale simulator config must be an object")
    else:
        if not 10.0 <= float(config.get("dense_int8_peak_tops", 0.0)) <= 50.0:
            errors.append("first open target must model 10-50 dense INT8 TOPS")
        if int(config.get("dma_queue_depth", 0)) < 1024:
            errors.append("first open target must model descriptor queue depth >=1024")
        if int(config.get("scratchpad_kib", 0)) < 1024:
            errors.append("first open target must model at least 1 MiB aggregate scratchpad")
        precision_matrix = config.get("precision_matrix")
        if not isinstance(precision_matrix, list):
            errors.append("scale simulator config must report precision_matrix")
        else:
            states = {
                entry.get("precision"): entry.get("state")
                for entry in precision_matrix
                if isinstance(entry, dict)
            }
            missing = sorted(REQUIRED_PRECISIONS - set(states))
            if missing:
                errors.append(f"precision_matrix missing: {', '.join(missing)}")
            if states.get("FP8") != "blocked":
                errors.append("precision_matrix must keep FP8 blocked")
            for projected in ("FP16", "BF16"):
                if states.get(projected) != "projected":
                    errors.append(f"precision_matrix must report {projected} as projected only")
        descriptor_queue = config.get("descriptor_queue")
        if not isinstance(descriptor_queue, dict):
            errors.append("scale simulator config must report descriptor_queue")
        elif (
            descriptor_queue.get("runtime_mmio_support")
            != "reserved_blocked_without_dma_engine_evidence"
        ):
            errors.append("descriptor_queue must not claim implemented runtime MMIO support")

    artifacts = data.get("artifacts", {})
    model = artifacts.get("model") if isinstance(artifacts, dict) else None
    if not isinstance(model, dict):
        errors.append("scale simulator must capture benchmark model hash")
    else:
        if model.get("path") != "benchmarks/models/mobile_smoke.tflite":
            errors.append("model hash path must identify mobile_smoke.tflite")
        sha = model.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            errors.append("model hash must be sha256 hex")
        if not isinstance(model.get("bytes"), int) or model.get("bytes", 0) <= 0:
            errors.append("model hash must include positive byte size")

    kernels = data.get("kernels")
    if not isinstance(kernels, list) or len(kernels) < 3:
        errors.append("scale simulator must report at least GEMM, conv, and attention kernels")
    else:
        names = {kernel.get("kernel") for kernel in kernels if isinstance(kernel, dict)}
        for required in ("gemm_s8", "conv2d_s8", "attention_qk_s8"):
            if required not in names:
                errors.append(f"scale simulator missing kernel {required}")
        for index, kernel in enumerate(kernels):
            if not isinstance(kernel, dict):
                errors.append(f"kernels[{index}] must be an object")
                continue
            missing = sorted(REQUIRED_KERNEL_KEYS - set(kernel))
            if missing:
                errors.append(f"kernels[{index}] missing keys: {', '.join(missing)}")
            for field in (
                "target_cycles",
                "npu_cycles",
                "macs",
                "bytes_read",
                "bytes_written",
                "modeled_frequency_hz",
            ):
                value = kernel.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    errors.append(f"kernels[{index}].{field} must be a positive integer")
            for field in ("utilization_percent", "throughput_ops_s", "observed_tops"):
                value = kernel.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    errors.append(f"kernels[{index}].{field} must be positive numeric")

    return report(errors)


def report(errors: list[str]) -> int:
    clean = [error for error in errors if error]
    if clean:
        print("NPU scale simulator check failed:")
        for error in clean:
            print(f"  - {error}")
        return 1
    print("NPU scale simulator check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
