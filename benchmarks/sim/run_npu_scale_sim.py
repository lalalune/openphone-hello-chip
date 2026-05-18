#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from compiler.runtime.hello_npu_scale_model import (  # noqa: E402
    MIN_REAL_V1,
    OPEN_2028_FIRST,
    OPEN_2028_STRETCH,
    NpuScaleConfig,
    estimate_attention_qk_s8,
    estimate_conv2d_s8,
    estimate_gemm_s8,
)

CONFIGS = {
    MIN_REAL_V1.name: MIN_REAL_V1,
    OPEN_2028_FIRST.name: OPEN_2028_FIRST,
    OPEN_2028_STRETCH.name: OPEN_2028_STRETCH,
}
MODEL = ROOT / "benchmarks/models/mobile_smoke.tflite"


def file_hash(path: Path) -> dict[str, str | int]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
    }


def build_workload(config: NpuScaleConfig):
    return [
        estimate_gemm_s8(config, 4096, 4096, 4096),
        estimate_gemm_s8(config, 1024, 1024, 4096),
        estimate_conv2d_s8(config, 1, 56, 56, 256, 256, 3, 3),
        estimate_attention_qk_s8(config, 1, 16, 2048, 2048, 128),
    ]


def metric_entry(config: NpuScaleConfig, estimate) -> dict:
    memory_wait_cycles = max(0, estimate.memory_cycles - estimate.compute_cycles)
    stall_cycles = max(0, estimate.cycles - estimate.compute_cycles)
    utilization = 100.0 * estimate.compute_cycles / estimate.cycles
    elapsed_s = estimate.cycles / config.clock_hz
    return {
        "kernel": estimate.kernel,
        "target_cycles": estimate.cycles,
        "npu_cycles": estimate.cycles,
        "macs": estimate.macs,
        "bytes_read": estimate.bytes_read,
        "bytes_written": estimate.bytes_written,
        "compute_cycles": estimate.compute_cycles,
        "memory_cycles": estimate.memory_cycles,
        "memory_wait_cycles": memory_wait_cycles,
        "stall_cycles": stall_cycles,
        "utilization_percent": utilization,
        "modeled_frequency_hz": config.clock_hz,
        "throughput_ops_s": (estimate.macs * 2) / elapsed_s,
        "observed_tops": estimate.observed_tops(config.clock_hz),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic NPU architecture scale model")
    parser.add_argument("--config", choices=sorted(CONFIGS), default=OPEN_2028_FIRST.name)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    config = CONFIGS[args.config]
    kernels = [metric_entry(config, estimate) for estimate in build_workload(config)]
    report = {
        "schema": "openphone.npu_scale_sim.v1",
        "config": {
            "name": config.name,
            "tiles": config.tiles,
            "int8_macs_per_tile_per_cycle": config.int8_macs_per_tile_per_cycle,
            "int8_macs_per_cycle": config.int8_macs_per_cycle,
            "clock_hz": config.clock_hz,
            "scratchpad_kib": config.scratchpad_kib,
            "dma_queue_depth": config.dma_queue_depth,
            "dma_bytes_per_cycle": config.dma_bytes_per_cycle,
            "dense_int8_peak_tops": config.dense_int8_peak_tops,
            "sparse_int4_peak_tops": config.sparse_int4_peak_tops,
            "supports_int4": config.supports_int4,
            "supports_bf16": config.supports_bf16,
            "supports_fp16": config.supports_fp16,
            "supports_fp8": config.supports_fp8,
            "precision_matrix": config.precision_matrix(),
            "descriptor_queue": {
                "depth": config.dma_queue_depth,
                "submission_api": "modeled_only",
                "runtime_mmio_support": "reserved_blocked_without_dma_engine_evidence",
            },
        },
        "artifacts": {
            "model": file_hash(MODEL),
            "benchmark_model_hash_capture": "sha256",
        },
        "kernels": kernels,
        "summary": {
            "kernel_count": len(kernels),
            "total_macs": sum(kernel["macs"] for kernel in kernels),
            "total_bytes_read": sum(kernel["bytes_read"] for kernel in kernels),
            "total_bytes_written": sum(kernel["bytes_written"] for kernel in kernels),
            "min_observed_tops": min(kernel["observed_tops"] for kernel in kernels),
            "max_observed_tops": max(kernel["observed_tops"] for kernel in kernels),
            "min_utilization_percent": min(kernel["utilization_percent"] for kernel in kernels),
        },
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = args.out if args.out.is_absolute() else ROOT / args.out
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
