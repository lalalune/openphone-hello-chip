#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/spec-db/npu-2028-target.yaml"
DOC = ROOT / "docs/npu/2028-targets.md"
RTL = ROOT / "rtl/npu/hello_npu.sv"
COCOTB = ROOT / "verify/cocotb/test_hello_npu.py"
ARCH = ROOT / "docs/arch/npu.md"


MIN_TARGETS = {
    "dense_int8_peak_tops_min": 160,
    "dense_int8_sustained_tops_min": 80,
    "sparse_int4_peak_tops_min": 512,
    "sparse_int4_sustained_tops_min": 200,
    "int2_bitnet_peak_tops_min": 900,
    "fp8_peak_tflops_min": 80,
    "sustained_perf_per_w_int8_tops_min": 18,
    "local_sram_mib_min": 64,
    "local_sram_bandwidth_tbps_min": 20,
    "shared_system_cache_mib_min": 32,
    "external_memory_bandwidth_gbps_min": 180,
    "command_queue_depth_min": 1024,
    "concurrent_contexts_min": 8,
}

REQUIRED_PRECISIONS = {
    "int8",
    "int4",
    "int2",
    "fp8",
    "bf16",
    "fp16",
    "int32_accumulate",
}

REQUIRED_SOURCES = {
    "https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-elite-gen-5",
    "https://www.mediatek.com/products/smartphones/mediatek-dimensity-9500",
    "https://semiconductor.samsung.com/processor/mobile-processor/exynos-2600/",
    "https://www.qualcomm.com/laptops/products/snapdragon-x-elite",
    "https://support.apple.com/en-us/125090",
}


def main() -> int:
    errors: list[str] = []

    for path in (SPEC, DOC, RTL, COCOTB, ARCH):
        if not path.is_file():
            errors.append(f"missing required NPU target artifact: {path.relative_to(ROOT)}")
    if errors:
        return report(errors)

    spec = yaml.safe_load(SPEC.read_text())
    if spec.get("schema") != "openphone.npu_2028_target.v1":
        errors.append("unexpected NPU target schema")
    if spec.get("target_year") != 2028:
        errors.append("NPU target_year must remain 2028")
    if spec.get("target_class") != "performance_heavy_android_phone_ap":
        errors.append("NPU target_class must identify the performance-heavy Android phone AP goal")

    numeric = spec.get("numeric_targets", {})
    for key, minimum in MIN_TARGETS.items():
        value = numeric.get(key)
        if not isinstance(value, (int, float)) or value < minimum:
            errors.append(f"numeric target {key} must be >= {minimum}; got {value!r}")

    precisions = set(spec.get("precision_requirements", {}).get("required", []))
    missing_precision = sorted(REQUIRED_PRECISIONS - precisions)
    if missing_precision:
        errors.append("missing required precision target(s): " + ", ".join(missing_precision))

    source_urls = {entry.get("source_url") for entry in spec.get("source_anchors", [])}
    missing_sources = sorted(REQUIRED_SOURCES - source_urls)
    if missing_sources:
        errors.append("missing source anchor(s): " + ", ".join(missing_sources))

    classification = spec.get("current_repo_classification", {})
    if classification.get("level") != "L0_RTL_UNIT":
        errors.append(
            "current repo NPU classification must stay L0_RTL_UNIT until higher evidence exists"
        )
    gaps = set(classification.get("explicit_gaps", []))
    for gap in (
        "no_systolic_array",
        "no_compiler_backend",
        "no_NNAPI_delegate",
        "no_sustained_benchmark_evidence",
    ):
        if gap not in gaps:
            errors.append(f"current repo classification must explicitly retain gap: {gap}")

    rtl_text = RTL.read_text()
    cocotb_text = COCOTB.read_text()
    arch_text = ARCH.read_text()
    doc_text = DOC.read_text()
    for token, path_text, path in (
        ("OP_DOT8_S4", rtl_text, RTL),
        ("dot8_s4_sum", rtl_text, RTL),
        ("pack_s4", cocotb_text, COCOTB),
        ("DOT8_S4", arch_text, ARCH),
        ("Dense INT8 peak", doc_text, DOC),
        ("CPU fallback", doc_text, DOC),
    ):
        if token not in path_text:
            errors.append(f"{path.relative_to(ROOT)} missing required token {token!r}")

    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("NPU 2028 target check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
