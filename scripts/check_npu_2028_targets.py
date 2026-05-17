#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/spec-db/npu-2028-target.yaml"
DOC = ROOT / "docs/npu/2028-targets.md"
RTL = ROOT / "rtl/npu/hello_npu.sv"
COCOTB = ROOT / "verify/cocotb/test_hello_npu.py"
ARCH = ROOT / "docs/arch/npu.md"
MEMORY_MAP = ROOT / "docs/arch/memory-map.md"
CONTRACT = ROOT / "sw/platform/hello_platform_contract.json"
RUNTIME = ROOT / "compiler/runtime/hello_npu_runtime.py"
BENCH_CONFIG = ROOT / "benchmarks/configs/benchmark_plan.json"
PROOF_TEMPLATE = ROOT / "docs/benchmarks/capabilities/hello_npu_nnapi.proof.template.json"
CAPABILITY_README = ROOT / "docs/benchmarks/capabilities/README.md"
REPORT_SCHEMA = ROOT / "docs/benchmarks/report-schema.yaml"


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

RUNTIME_REGISTER_ALIASES = {
    "TRACE": "DEBUG",
}

REQUIRED_NPU_PROOF_FIELDS = {
    "capability.claim_level",
    "capability.precision",
    "dataflow.name",
    "dma.path",
    "dma.bytes_read",
    "dma.bytes_written",
    "measurements.macs_per_inference",
    "measurements.npu_cycles",
    "measurements.npu_hz",
    "measurements.observed_tops",
    "measurements.tops_formula",
}

REQUIRED_NPU_PROOF_TRANSCRIPTS = {
    "adb_devices",
    "nnapi_accelerator_query",
    "benchmark_model_nnapi",
    "dma_trace",
}


def h(value: str) -> int:
    return int(value.replace("_", ""), 16)


def parse_runtime_constants(text: str) -> dict[str, int]:
    constants: dict[str, int] = {}
    for name, value in re.findall(r"(?m)^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*([0-9A-Fa-f_x]+)", text):
        constants[name] = int(value.replace("_", ""), 0)
    return constants


def dotted_present(data: dict, path: str) -> bool:
    value = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return value not in (None, "", [], {})


def find_benchmark(config: dict, name: str) -> dict | None:
    for bench in config.get("benchmarks", []):
        if bench.get("name") == name:
            return bench
    return None


def check_runtime_contract(errors: list[str]) -> None:
    contract = json.loads(CONTRACT.read_text())
    regions = {region["name"]: region for region in contract["hello_chip"]["regions"]}
    npu = regions["npu"]
    npu_base = h(npu["base"])
    constants = parse_runtime_constants(RUNTIME.read_text())

    for reg in npu["registers"]:
        name = reg["name"]
        if name.startswith("SCRATCH"):
            continue
        runtime_name = RUNTIME_REGISTER_ALIASES.get(name, name)
        expected = npu_base + h(reg["offset"])
        actual = constants.get(runtime_name)
        if actual != expected:
            errors.append(
                f"compiler/runtime/hello_npu_runtime.py constant {runtime_name} "
                f"must be 0x{expected:08X}; got {actual!r}"
            )

    if constants.get("SCRATCH") != npu_base + 0x80:
        errors.append("compiler/runtime/hello_npu_runtime.py SCRATCH must point to NPU offset 0x80")
    if constants.get("SCRATCH_BYTES") != 64:
        errors.append("compiler/runtime/hello_npu_runtime.py SCRATCH_BYTES must remain 64")
    if constants.get("OP_DOT8_S4") != 7:
        errors.append("compiler/runtime/hello_npu_runtime.py must expose OP_DOT8_S4 = 7")


def check_benchmark_evidence_gates(errors: list[str]) -> None:
    config = json.loads(BENCH_CONFIG.read_text())
    bench = find_benchmark(config, "tflite_hello_npu")
    if bench is None:
        errors.append("benchmark plan missing tflite_hello_npu")
        return
    artifacts = bench.get("capability_artifacts", [])
    if len(artifacts) != 1:
        errors.append("tflite_hello_npu must have exactly one capability_artifact")
        return
    proof = artifacts[0].get("proof", {})
    required_fields = set(proof.get("required_json_fields", []))
    missing_fields = sorted(REQUIRED_NPU_PROOF_FIELDS - required_fields)
    if missing_fields:
        errors.append(
            "tflite_hello_npu proof missing required_json_fields: " + ", ".join(missing_fields)
        )
    required_files = set(proof.get("required_files", []))
    missing_files = sorted(REQUIRED_NPU_PROOF_TRANSCRIPTS - required_files)
    if missing_files:
        errors.append(
            "tflite_hello_npu proof missing required transcript(s): " + ", ".join(missing_files)
        )
    markers = proof.get("required_transcript_markers", {})
    for transcript in REQUIRED_NPU_PROOF_TRANSCRIPTS:
        if transcript not in markers:
            errors.append(f"tflite_hello_npu proof missing markers for {transcript}")
    for token in ("bytes_read", "bytes_written", "hello-npu", "DMA"):
        if token not in markers.get("dma_trace", []):
            errors.append(f"tflite_hello_npu dma_trace markers must include {token!r}")

    template = json.loads(PROOF_TEMPLATE.read_text())
    for field in REQUIRED_NPU_PROOF_FIELDS:
        if not dotted_present(template, field):
            errors.append(f"proof template missing required field {field}")
    transcripts = set(template.get("transcripts", {}))
    missing_template_transcripts = sorted(REQUIRED_NPU_PROOF_TRANSCRIPTS - transcripts)
    if missing_template_transcripts:
        errors.append(
            "proof template missing transcript(s): " + ", ".join(missing_template_transcripts)
        )

    for token, path in (
        ("observed_tops", CAPABILITY_README),
        ("macs_per_inference", CAPABILITY_README),
        ("dma_trace", CAPABILITY_README),
        ("MAC/cycle", REPORT_SCHEMA),
    ):
        if token not in path.read_text():
            errors.append(f"{path.relative_to(ROOT)} missing NPU evidence token {token!r}")


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

    for path in (
        SPEC,
        DOC,
        RTL,
        COCOTB,
        ARCH,
        MEMORY_MAP,
        CONTRACT,
        RUNTIME,
        BENCH_CONFIG,
        PROOF_TEMPLATE,
        CAPABILITY_README,
        REPORT_SCHEMA,
    ):
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
    memory_map_text = MEMORY_MAP.read_text()
    for token, path_text, path in (
        ("OP_DOT8_S4", rtl_text, RTL),
        ("dot8_s4_sum", rtl_text, RTL),
        ("pack_s4", cocotb_text, COCOTB),
        ("DOT8_S4", arch_text, ARCH),
        ("PERF_UNSUPPORTED_OPS", memory_map_text, MEMORY_MAP),
        ("SCRATCH[0..15]", memory_map_text, MEMORY_MAP),
        ("Dense INT8 peak", doc_text, DOC),
        ("CPU fallback", doc_text, DOC),
        ("observed_tops", doc_text, DOC),
        ("macs_per_inference", doc_text, DOC),
        ("dma", doc_text.lower(), DOC),
    ):
        if token not in path_text:
            errors.append(f"{path.relative_to(ROOT)} missing required token {token!r}")

    check_runtime_contract(errors)
    check_benchmark_evidence_gates(errors)

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
