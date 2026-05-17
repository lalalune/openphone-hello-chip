#!/usr/bin/env python3
"""Regression tests for benchmark parser and strict-missing behavior."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "benchmarks/run_benchmarks.py"
PLAN_PATH = ROOT / "benchmarks/configs/benchmark_plan.json"
BLOCKED_METADATA = ROOT / "benchmarks/metadata/strict-blocked-template.json"

spec = importlib.util.spec_from_file_location("run_benchmarks", RUNNER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not import {RUNNER_PATH}")
run_benchmarks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_benchmarks)


def run_runner(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(RUNNER_PATH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def test_suite_parsers_accept_real_formats() -> None:
    coremark = run_benchmarks.parse_coremark("Iterations/Sec   : 123.5\nCoreMark/MHz : 4.25\n")
    assert_equal(coremark["coremark_per_mhz"], 4.25, "CoreMark/MHz")

    stream = run_benchmarks.parse_stream("Copy: 10.0\nScale: 11.0\nAdd: 12.0\nTriad: 13.5\n")
    assert_equal(stream["triad_mb_per_s"], 13.5, "STREAM Triad")

    bw_mem = run_benchmarks.parse_lmbench_bw_mem("64.00 8192.25\n")
    assert_equal(bw_mem["bandwidth_mb_per_s"], 8192.25, "lmbench bandwidth")

    lat_mem = run_benchmarks.parse_lmbench_lat_mem_rd("0.00049 1.2\n64.0 98.5\n")
    assert_equal(lat_mem["max_latency_ns"], 98.5, "lmbench latency")

    fio = run_benchmarks.parse_fio_json(
        json.dumps({"jobs": [{"read": {"iops": 10, "bw": 2048}, "write": {"iops": 3, "bw": 512}}]})
    )
    assert_equal(fio["read_iops"], 10.0, "fio read iops")
    assert_equal(fio["write_bw_kib_s"], 512.0, "fio write bandwidth")

    tflite = run_benchmarks.parse_tflite_benchmark_model(
        "Inference timings in us: Init: 1, First inference: 2, Warmup (avg): 3, Inference (avg): 42.75\n"
        "CPU fallback: 0%\n"
        "unsupported ops: 0\n"
    )
    assert_equal(tflite["avg_latency_us"], 42.75, "TFLite avg latency")
    assert_equal(tflite["cpu_fallback_percent"], 0.0, "TFLite fallback")
    assert_equal(tflite["unsupported_op_count"], 0, "TFLite unsupported ops")


def test_parsers_reject_incomplete_or_comparable_metrics() -> None:
    rejects: list[tuple[str, Any, str]] = [
        ("coremark", run_benchmarks.parse_coremark, "Iterations/Sec : 123\n"),
        ("stream", run_benchmarks.parse_stream, "Copy: 1.0\n"),
        ("fio", run_benchmarks.parse_fio_json, json.dumps({"jobs": [{"read": {}, "write": {}}]})),
        ("tflite", run_benchmarks.parse_tflite_benchmark_model, "unsupported ops: 0\n"),
        (
            "simulator",
            run_benchmarks.parse_simulator_metrics,
            json.dumps(
                {
                    "target_cycles": 1,
                    "simulated_frequency_hz": 1,
                    "ipc": 1,
                    "benchmark_success_allowed": False,
                }
            ),
        ),
        (
            "simulator_score",
            run_benchmarks.parse_simulator_metrics,
            json.dumps(
                {
                    "target_cycles": 1,
                    "simulated_frequency_hz": 1,
                    "ipc": 1,
                    "benchmark_success_allowed": True,
                    "phone_score": 99,
                }
            ),
        ),
    ]
    for name, parser, output in rejects:
        try:
            parser(output)
        except (ValueError, json.JSONDecodeError):
            continue
        raise AssertionError(f"{name} parser unexpectedly accepted invalid evidence")


def test_simulator_parser_accepts_calibrated_counter_export_shape() -> None:
    metrics = run_benchmarks.parse_simulator_metrics(
        json.dumps(
            {
                "target_cycles": 1000,
                "simulated_frequency_hz": 500_000_000,
                "ipc": 0.5,
                "mpki": 2.0,
                "benchmark_success_allowed": True,
            }
        )
    )
    assert_equal(metrics["target_cycles"], 1000, "simulator cycles")
    assert_equal(metrics["benchmark_success_allowed"], True, "simulator success flag")


def test_strict_missing_exits_two_and_preserves_blockers() -> None:
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        temp_plan = temp_root / "benchmark_plan_missing_assets.json"
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        for bench in plan["benchmarks"]:
            if bench["name"] == "coremark":
                bench["requires"] = ["definitely_missing_openphone_coremark"]
            for artifact in bench.get("model_artifacts", []):
                artifact["path"] = "benchmarks/models/definitely_missing_mobile_smoke.tflite"
        temp_plan.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        out_dir = Path(td) / "out"
        result = run_runner(
            [
                "plan",
                "--config",
                str(temp_plan),
                "--out-dir",
                str(out_dir),
                "--strict-missing",
                "--report-id",
                "strict-missing",
            ]
        )
        report = json.loads((out_dir / "strict-missing/report.json").read_text(encoding="utf-8"))

    if result.returncode != 2:
        raise AssertionError(result.stdout)
    result_by_name = {row["name"]: row for row in report["results"]}
    assert_equal(
        result_by_name["coremark"]["status"], "planned_missing_deps", "coremark strict status"
    )
    assert_equal(result_by_name["tflite_cpu"]["status"], "blocked", "tflite strict status")
    blocked = result_by_name["tflite_cpu"].get("blocked_assets", [])
    if not blocked:
        raise AssertionError(json.dumps(result_by_name["tflite_cpu"], indent=2))
    assert_equal(blocked[0]["blocker_id"], "TFLITE_SMOKE_MODEL_MISSING", "tflite blocker id")
    assert_equal(blocked[0]["pipeline_visible"], True, "tflite pipeline visibility")
    assert_equal(blocked[0]["release_blocking"], True, "tflite release blocker")


def test_blocked_metadata_template_covers_config_assets() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(BLOCKED_METADATA.read_text(encoding="utf-8"))
    assets = metadata["calibration"]["assets"]
    expected_assets = sorted(
        {
            asset
            for bench in plan["benchmarks"]
            for asset in bench.get("required_calibration_assets", [])
        }
    )
    missing = [asset for asset in expected_assets if asset not in assets]
    if missing:
        raise AssertionError("blocked metadata template missing asset(s): " + ", ".join(missing))
    for asset_name in expected_assets:
        asset = assets[asset_name]
        assert_equal(asset.get("status"), "blocked", f"{asset_name} status")
        for field in ("source", "sha256", "evidence"):
            value = asset.get(field)
            if not isinstance(value, str) or not value.startswith("blocked-"):
                raise AssertionError(f"{asset_name}.{field} must be a blocked marker")


def main() -> int:
    for test in (
        test_suite_parsers_accept_real_formats,
        test_parsers_reject_incomplete_or_comparable_metrics,
        test_simulator_parser_accepts_calibrated_counter_export_shape,
        test_strict_missing_exits_two_and_preserves_blockers,
        test_blocked_metadata_template_covers_config_assets,
    ):
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
