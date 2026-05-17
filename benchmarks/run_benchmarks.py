#!/usr/bin/env python3
"""OpenPhone benchmark harness.

This runner is intentionally conservative: it can plan benchmark commands before
the tools exist, records missing dependencies and unavailable model assets as
structured results, validates generated reports, and avoids shell execution so
command lines stay explicit.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Any


DEFAULT_CONFIG = Path("benchmarks/configs/benchmark_plan.json")
DEFAULT_OUT_DIR = Path("benchmarks/results")
COMMANDS = {"list", "plan", "run", "validate-report"}
VALID_CLAIM_LEVELS = {
    "L0_RTL_UNIT",
    "L1_RTL_FULL_SOC",
    "L2_ARCH_SIM",
    "L3_FPGA",
    "L4_DEV_BOARD",
    "L5_PROTOTYPE_SILICON",
    "L6_COMPLETE_PHONE",
}
VALID_RESULT_STATUSES = {
    "planned",
    "planned_missing_deps",
    "blocked",
    "missing_dependencies",
    "passed",
    "failed",
    "timeout",
    "error",
}
VALID_PARSERS = {
    "coremark_v1",
    "stream_v5",
    "lmbench_bw_mem",
    "lmbench_lat_mem_rd",
    "fio_json_v3",
    "tflite_benchmark_model",
    "simulator_metrics_v1",
}
VALID_PROVENANCE = {"dry_run", "measured", "simulator", "imported"}
REAL_METADATA_SECTIONS = ("software", "clocks", "memory", "thermal", "power", "calibration")
REAL_METADATA_REQUIRED_FIELDS = {
    "software": {
        "os": str,
        "kernel": str,
        "firmware": str,
        "runtime": str,
        "build_id": str,
    },
    "clocks": {
        "source": str,
        "cpu_hz": (int, float),
        "npu_hz": (int, float),
        "memory_hz": (int, float),
        "governor": str,
    },
    "memory": {
        "type": str,
        "capacity_bytes": int,
        "bandwidth_bytes_per_second": (int, float),
        "channels": int,
    },
    "thermal": {
        "ambient_c": (int, float),
        "die_c": (int, float),
        "cooling": str,
        "throttle_state": str,
    },
    "power": {
        "source": str,
        "watts": (int, float),
        "measurement_method": str,
        "sample_count": int,
        "averaging_window_seconds": (int, float),
    },
    "calibration": {
        "status": str,
        "source": str,
        "ground_truth_reference": str,
        "last_calibrated_utc": str,
        "assets": dict,
    },
}
REQUIRED_REPORT_FIELDS = {
    "schema": str,
    "report_id": str,
    "date_utc": str,
    "dry_run": bool,
    "claim_level": str,
    "platform": dict,
    "config": dict,
    "results": list,
}
REQUIRED_RESULT_FIELDS = {
    "name": str,
    "suite": str,
    "version": str,
    "command": list,
    "input_dataset": str,
    "primary_metric": str,
    "units": str,
    "dependencies": list,
    "artifacts": dict,
    "status": str,
}
STRICT_RESULT_METADATA_FIELDS = {
    "provenance": str,
    "parser": str,
}
BLOCKED_PREFIX = "blocked-"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    if "benchmarks" not in config or not isinstance(config["benchmarks"], list):
        raise ValueError(f"{path} must contain a benchmarks list")
    validate_config(config, path)
    return config


def validate_config(config: dict[str, Any], path: Path) -> None:
    names: set[str] = set()
    for index, bench in enumerate(config["benchmarks"]):
        location = f"{path}: benchmarks[{index}]"
        for key in ("name", "suite", "version", "command", "primary_metric", "units", "parser"):
            if key not in bench:
                raise ValueError(f"{location} missing required key {key!r}")
        if not isinstance(bench["name"], str) or not bench["name"]:
            raise ValueError(f"{location} name must be a non-empty string")
        if bench["name"] in names:
            raise ValueError(f"{location} duplicate benchmark name {bench['name']!r}")
        names.add(bench["name"])
        if not isinstance(bench["command"], list) or not all(isinstance(part, str) for part in bench["command"]):
            raise ValueError(f"{location} command must be a list of strings")
        if bench["parser"] not in VALID_PARSERS:
            raise ValueError(f"{location} parser {bench['parser']!r} is not supported")
        if "provenance" in bench and bench["provenance"] not in VALID_PROVENANCE:
            raise ValueError(f"{location} provenance {bench['provenance']!r} is not supported")
        for list_key in ("required_metadata", "required_metrics"):
            if list_key in bench and not isinstance(bench[list_key], list):
                raise ValueError(f"{location} {list_key} must be a list")
            for item in bench.get(list_key, []):
                if not isinstance(item, str) or not item:
                    raise ValueError(f"{location} {list_key} entries must be non-empty strings")
        if "required_calibration_assets" in bench and not isinstance(bench["required_calibration_assets"], list):
            raise ValueError(f"{location} required_calibration_assets must be a list")
        for item in bench.get("required_calibration_assets", []):
            if not isinstance(item, str) or not item:
                raise ValueError(f"{location} required_calibration_assets entries must be non-empty strings")
        if "metric_gates" in bench and not isinstance(bench["metric_gates"], list):
            raise ValueError(f"{location} metric_gates must be a list")
        for gate_index, gate in enumerate(bench.get("metric_gates", [])):
            gate_location = f"{location} metric_gates[{gate_index}]"
            if not isinstance(gate, dict):
                raise ValueError(f"{gate_location} must be an object")
            if not isinstance(gate.get("metric"), str) or not gate["metric"]:
                raise ValueError(f"{gate_location}.metric must be a non-empty string")
            if gate.get("op") not in {"==", "!=", "<", "<=", ">", ">="}:
                raise ValueError(f"{gate_location}.op must be one of ==, !=, <, <=, >, >=")
            if not isinstance(gate.get("value"), (int, float)):
                raise ValueError(f"{gate_location}.value must be numeric")
        for list_key in ("requires", "required_files", "model_artifacts"):
            if list_key in bench and not isinstance(bench[list_key], list):
                raise ValueError(f"{location} {list_key} must be a list")
        for asset in bench.get("model_artifacts", []):
            if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
                raise ValueError(f"{location} model_artifacts entries must contain a string path")
            for bool_key in ("pipeline_visible", "release_blocking"):
                if bool_key in asset and not isinstance(asset[bool_key], bool):
                    raise ValueError(f"{location} model_artifacts {bool_key} must be a boolean")
            if asset.get("placeholder_allowed") is True and asset.get("release_blocking", True) is True:
                raise ValueError(f"{location} release-blocking model artifacts must not allow placeholders")
            if "generator" in asset:
                generator = asset["generator"]
                if not isinstance(generator, dict) or not isinstance(generator.get("command"), list):
                    raise ValueError(f"{location} model_artifacts generator.command must be a list")
                if not all(isinstance(part, str) for part in generator["command"]):
                    raise ValueError(f"{location} model_artifacts generator.command must contain strings")


def source_tree_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def command_available(executable: str, root: Path) -> tuple[bool, str | None]:
    candidate = Path(executable)
    if candidate.parts and (candidate.is_absolute() or len(candidate.parts) > 1):
        resolved = candidate if candidate.is_absolute() else root / candidate
        return resolved.exists() and os.access(resolved, os.X_OK), str(resolved)

    resolved = shutil.which(executable)
    return resolved is not None, resolved


def dependency_status(bench: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for dep in bench.get("requires", []):
        ok, resolved = command_available(dep, root)
        statuses.append({"name": dep, "kind": "executable", "available": ok, "path": resolved})
    for artifact in bench.get("required_files", []):
        path = root / artifact
        statuses.append({"name": artifact, "kind": "file", "available": path.is_file(), "path": str(path)})
    for artifact in bench.get("model_artifacts", []):
        statuses.append(model_artifact_status(artifact, root))
    return statuses


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_artifact_status(artifact: dict[str, Any], root: Path) -> dict[str, Any]:
    path = root / artifact["path"]
    status: dict[str, Any] = {
        "name": artifact["path"],
        "kind": "model_artifact",
        "available": path.is_file(),
        "path": str(path),
        "placeholder_allowed": bool(artifact.get("placeholder_allowed", False)),
        "blocker_id": artifact.get("blocker_id", "MODEL_ARTIFACT_UNAVAILABLE"),
        "pipeline_visible": bool(artifact.get("pipeline_visible", True)),
        "release_blocking": bool(artifact.get("release_blocking", True)),
    }
    if artifact.get("generator"):
        status["generator"] = artifact["generator"]
    if artifact.get("resolution"):
        status["resolution"] = artifact["resolution"]
    if not path.is_file():
        status["blocked_reason"] = "missing_model_artifact"
        return status

    digest = sha256_file(path)
    status["sha256"] = digest
    expected_sha256 = artifact.get("sha256")
    placeholder_sha256 = set(artifact.get("placeholder_sha256", []))
    min_size_bytes = int(artifact.get("min_size_bytes", 1))
    size = path.stat().st_size
    status["size_bytes"] = size

    if expected_sha256 and digest != expected_sha256:
        status["available"] = False
        status["blocked_reason"] = "model_sha256_mismatch"
    elif digest in placeholder_sha256 or size < min_size_bytes:
        status["available"] = False
        status["blocked_reason"] = "placeholder_model_artifact"
    return status


def missing_dependencies(statuses: list[dict[str, Any]]) -> list[str]:
    return [
        item["name"]
        for item in statuses
        if not item["available"] and item.get("kind") != "model_artifact"
    ]


def missing_dependency_blockers(bench: dict[str, Any], statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    install = bench.get("install", "")
    for item in statuses:
        if item["available"] or item.get("kind") == "model_artifact":
            continue
        kind = item.get("kind", "dependency")
        if kind == "executable":
            command = f"Install/build {item['name']} for the target and put it on PATH, then rerun this benchmark."
        elif kind == "file":
            command = f"Create or copy {item['name']} into the repository, then rerun this benchmark."
        else:
            command = f"Provide missing {kind} {item['name']}, then rerun this benchmark."
        blockers.append(
            {
                "name": item["name"],
                "kind": kind,
                "reason": f"missing_{kind}",
                "resolution": install or command,
            }
        )
    return blockers


def blocked_assets(statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "reason": item.get("blocked_reason", "unavailable_model_artifact"),
            "blocker_id": item.get("blocker_id", "MODEL_ARTIFACT_UNAVAILABLE"),
            "pipeline_visible": item.get("pipeline_visible", True),
            "release_blocking": item.get("release_blocking", True),
            "resolution": item.get("resolution", ""),
        }
        for item in statuses
        if not item["available"] and item.get("kind") == "model_artifact"
    ]


def is_blocked_value(value: Any) -> bool:
    return isinstance(value, str) and value.strip().startswith(BLOCKED_PREFIX)


def metadata_blockers(report: dict[str, Any], bench: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    required_sections = bench.get("required_metadata", list(REAL_METADATA_SECTIONS))
    for section in required_sections:
        if section not in REAL_METADATA_REQUIRED_FIELDS:
            continue
        data = report.get(section)
        if not isinstance(data, dict):
            blockers.append(
                {
                    "name": section,
                    "kind": "metadata",
                    "reason": "missing_metadata_section",
                    "resolution": f"Populate {section} in --metadata JSON before running real benchmarks.",
                }
            )
            continue
        for field in REAL_METADATA_REQUIRED_FIELDS[section]:
            value = data.get(field)
            if value is None or is_blocked_value(value):
                blockers.append(
                    {
                        "name": f"{section}.{field}",
                        "kind": "metadata",
                        "reason": "blocked_metadata_field",
                        "resolution": f"Replace {section}.{field} with measured target evidence in --metadata JSON.",
                    }
                )
    calibration = report.get("calibration")
    if isinstance(calibration, dict):
        if calibration.get("status") != "calibrated":
            blockers.append(
                {
                    "name": "calibration.status",
                    "kind": "calibration",
                    "reason": "uncalibrated_metadata",
                    "resolution": "Set calibration.status to calibrated only after clock, power, workload, and simulator evidence assets are recorded.",
                }
            )
        assets = calibration.get("assets") if isinstance(calibration.get("assets"), dict) else {}
        for asset_name in bench.get("required_calibration_assets", []):
            asset = assets.get(asset_name) if isinstance(assets, dict) else None
            if not isinstance(asset, dict):
                blockers.append(
                    {
                        "name": f"calibration.assets.{asset_name}",
                        "kind": "calibration",
                        "reason": "missing_calibration_asset",
                        "resolution": f"Add calibrated asset {asset_name} with source, sha256, and evidence fields.",
                    }
                )
                continue
            if asset.get("status") != "calibrated":
                blockers.append(
                    {
                        "name": f"calibration.assets.{asset_name}.status",
                        "kind": "calibration",
                        "reason": "uncalibrated_asset",
                        "resolution": f"Record calibrated evidence for {asset_name} before accepting this result.",
                    }
                )
            for field in ("source", "sha256", "evidence"):
                value = asset.get(field)
                if not isinstance(value, str) or not value.strip() or is_blocked_value(value):
                    blockers.append(
                        {
                            "name": f"calibration.assets.{asset_name}.{field}",
                            "kind": "calibration",
                            "reason": "blocked_calibration_field",
                            "resolution": f"Populate calibration.assets.{asset_name}.{field} with immutable evidence.",
                        }
                    )
    return blockers


def selected_benchmarks(config: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    benches = config["benchmarks"]
    if not names or "all" in names:
        return benches
    selected = [bench for bench in benches if bench["name"] in names]
    found = {bench["name"] for bench in selected}
    missing = sorted(names - found)
    if missing:
        raise ValueError("unknown benchmark(s): " + ", ".join(missing))
    return selected


def base_report(args: argparse.Namespace, config: dict[str, Any], root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "openphone.benchmark_run.v1",
        "report_id": args.report_id,
        "date_utc": utc_now(),
        "dry_run": args.dry_run,
        "claim_level": args.claim_level,
        "platform": {
            "name": args.platform,
            "revision": args.platform_revision,
            "source_tree_sha": source_tree_sha(root),
            "host": socket.gethostname(),
            "host_system": platform.platform(),
        },
        "config": {
            "path": str(args.config),
            "version": config.get("version", "unknown"),
        },
        "results": [],
    }
    metadata_path = args.metadata if getattr(args, "metadata", None) else None
    if metadata_path:
        resolved = metadata_path if metadata_path.is_absolute() else root / metadata_path
        with resolved.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
        for key in REAL_METADATA_SECTIONS:
            if key in metadata:
                report[key] = metadata[key]
    return report


def parse_coremark(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in output.splitlines():
        if "Iterations/Sec" in line:
            match = re.search(r"Iterations/Sec\s*:?\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
            if match:
                metrics["iterations_per_second"] = float(match.group(1))
        if "CoreMark/MHz" in line:
            match = re.search(r"CoreMark/MHz\s*:?\s*([0-9]+(?:\.[0-9]+)?)", line)
            if match:
                metrics["coremark_per_mhz"] = float(match.group(1))
    if "coremark_per_mhz" not in metrics:
        raise ValueError("CoreMark parser did not find CoreMark/MHz")
    return metrics


def parse_stream(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in output.splitlines():
        match = re.match(r"\s*(Copy|Scale|Add|Triad):\s+([0-9]+(?:\.[0-9]+)?)", line)
        if match:
            metrics[match.group(1).lower() + "_mb_per_s"] = float(match.group(2))
    if "triad_mb_per_s" not in metrics:
        raise ValueError("STREAM parser did not find Triad bandwidth")
    return metrics


def parse_lmbench_bw_mem(output: str) -> dict[str, Any]:
    values: list[float] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                values.append(float(parts[-1]))
            except ValueError:
                pass
    if not values:
        raise ValueError("lmbench bw_mem parser did not find bandwidth values")
    return {"bandwidth_mb_per_s": values[-1]}


def parse_lmbench_lat_mem_rd(output: str) -> dict[str, Any]:
    points: list[dict[str, float]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                points.append({"size_mb": float(parts[0]), "latency_ns": float(parts[1])})
            except ValueError:
                pass
    if not points:
        raise ValueError("lmbench lat_mem_rd parser did not find latency points")
    return {"points": points, "max_latency_ns": max(point["latency_ns"] for point in points)}


def parse_fio_json(output: str) -> dict[str, Any]:
    data = json.loads(output)
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("fio JSON output missing jobs")
    totals = {"read_iops": 0.0, "write_iops": 0.0, "read_bw_kib_s": 0.0, "write_bw_kib_s": 0.0}
    for job in jobs:
        read = job.get("read", {})
        write = job.get("write", {})
        totals["read_iops"] += float(read.get("iops", 0.0))
        totals["write_iops"] += float(write.get("iops", 0.0))
        totals["read_bw_kib_s"] += float(read.get("bw", 0.0))
        totals["write_bw_kib_s"] += float(write.get("bw", 0.0))
    if not any(totals.values()):
        raise ValueError("fio JSON output did not contain non-zero IO metrics")
    return totals


def parse_tflite_benchmark_model(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in output.splitlines():
        avg = re.search(r"Inference timings in us:.*avg=([0-9]+(?:\.[0-9]+)?)", line)
        if not avg:
            avg = re.search(r"\bavg[=:]\s*([0-9]+(?:\.[0-9]+)?)", line)
        if not avg:
            avg = re.search(
                r"Inference timings in us:.*Inference\s+\(avg\):\s*([0-9]+(?:\.[0-9]+)?)",
                line,
            )
        if avg:
            metrics["avg_latency_us"] = float(avg.group(1))
        fallback = re.search(r"CPU fallback(?: percent| percentage)?[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*%?", line, re.IGNORECASE)
        if not fallback:
            fallback = re.search(r"cpu_fallback_percent\s*[=:]\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
        if fallback:
            metrics["cpu_fallback_percent"] = float(fallback.group(1))
        unsupported = re.search(r"unsupported ops?[^0-9]*([0-9]+)", line, re.IGNORECASE)
        if not unsupported:
            unsupported = re.search(r"unsupported_op_count\s*[=:]\s*([0-9]+)", line, re.IGNORECASE)
        if unsupported:
            metrics["unsupported_op_count"] = int(unsupported.group(1))
    if "avg_latency_us" not in metrics:
        raise ValueError("TFLite parser did not find average inference latency")
    return metrics


def parse_simulator_metrics(output: str) -> dict[str, Any]:
    data = json.loads(output)
    required = ("target_cycles", "simulated_frequency_hz", "ipc")
    missing = [key for key in required if not isinstance(data.get(key), (int, float))]
    if missing:
        raise ValueError("simulator metrics missing numeric keys: " + ", ".join(missing))
    forbidden = [key for key in ("wall_clock_score", "phone_score", "geekbench_score") if key in data]
    if forbidden:
        raise ValueError("simulator metrics contain forbidden comparable score keys: " + ", ".join(forbidden))
    if data.get("benchmark_success_allowed") is not True:
        raise ValueError("simulator metrics are not calibrated benchmark evidence")
    return data


def parse_metrics(parser: str, output: str) -> dict[str, Any]:
    parsers = {
        "coremark_v1": parse_coremark,
        "stream_v5": parse_stream,
        "lmbench_bw_mem": parse_lmbench_bw_mem,
        "lmbench_lat_mem_rd": parse_lmbench_lat_mem_rd,
        "fio_json_v3": parse_fio_json,
        "tflite_benchmark_model": parse_tflite_benchmark_model,
        "simulator_metrics_v1": parse_simulator_metrics,
    }
    return parsers[parser](output)


def metric_gate_passes(actual: int | float, op: str, expected: int | float) -> bool:
    if op == "==":
        return actual == expected
    if op == "!=":
        return actual != expected
    if op == "<":
        return actual < expected
    if op == "<=":
        return actual <= expected
    if op == ">":
        return actual > expected
    if op == ">=":
        return actual >= expected
    raise ValueError(f"unsupported metric gate op {op!r}")


def check_metric_requirements(metrics: dict[str, Any], run_metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for metric in run_metadata.get("required_metrics", []):
        if not isinstance(metric, str) or not metric:
            errors.append("required_metrics entries must be non-empty strings")
            continue
        if not isinstance(metrics.get(metric), (int, float)):
            errors.append(f"missing required metric {metric}")
    for gate_index, gate in enumerate(run_metadata.get("metric_gates", [])):
        if not isinstance(gate, dict):
            errors.append(f"metric_gates[{gate_index}] must be an object")
            continue
        metric = gate.get("metric")
        actual = metrics.get(metric)
        op = gate.get("op")
        expected = gate.get("value")
        if not isinstance(metric, str) or not metric:
            errors.append(f"metric_gates[{gate_index}].metric must be a non-empty string")
            continue
        elif op not in {"==", "!=", "<", "<=", ">", ">="}:
            errors.append(f"metric gate {metric} has unsupported op {op!r}")
            continue
        elif not isinstance(expected, (int, float)):
            errors.append(f"metric gate {metric} has non-numeric expected value")
            continue
        if not isinstance(actual, (int, float)):
            errors.append(f"metric gate {metric} has no numeric metric")
        elif not metric_gate_passes(actual, op, expected):
            errors.append(f"metric gate {metric} {op} {expected} failed with {actual}")
    return errors


def check_calibration_requirements(report: dict[str, Any], result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    calibration = report.get("calibration")
    if not isinstance(calibration, dict):
        return ["missing calibration metadata"]
    if calibration.get("status") != "calibrated":
        errors.append("calibration.status must be calibrated")
    for field in ("source", "ground_truth_reference", "last_calibrated_utc"):
        value = calibration.get(field)
        if not isinstance(value, str) or not value.strip() or value.startswith("blocked-"):
            errors.append(f"calibration.{field} must be populated with non-blocked evidence")
    assets = calibration.get("assets")
    if not isinstance(assets, dict):
        errors.append("calibration.assets must be object")
        assets = {}
    run_metadata = result.get("run_metadata", {})
    for asset_name in run_metadata.get("required_calibration_assets", []):
        asset = assets.get(asset_name)
        if not isinstance(asset, dict):
            errors.append(f"missing calibration asset {asset_name}")
            continue
        if asset.get("status") != "calibrated":
            errors.append(f"calibration asset {asset_name} status must be calibrated")
        for field in ("source", "sha256", "evidence"):
            value = asset.get(field)
            if not isinstance(value, str) or not value.strip() or value.startswith("blocked-"):
                errors.append(f"calibration asset {asset_name}.{field} must be populated with non-blocked evidence")
    return errors


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field, expected_type in REQUIRED_REPORT_FIELDS.items():
        if field not in report:
            errors.append(f"report missing {field}")
        elif not isinstance(report[field], expected_type):
            errors.append(f"report.{field} must be {expected_type.__name__}")

    if report.get("schema") != "openphone.benchmark_run.v1":
        errors.append("report.schema must be openphone.benchmark_run.v1")
    if report.get("claim_level") not in VALID_CLAIM_LEVELS:
        errors.append("report.claim_level is not a valid claim level")
    has_passed_results = any(
        isinstance(result, dict) and result.get("status") == "passed"
        for result in report.get("results", [])
    )
    if report.get("dry_run") is False and has_passed_results:
        for section in REAL_METADATA_SECTIONS:
            if not isinstance(report.get(section), dict):
                errors.append(f"real report missing metadata section {section}")
                continue
            for field, expected_type in REAL_METADATA_REQUIRED_FIELDS[section].items():
                value = report[section].get(field)
                if (
                    not isinstance(value, expected_type)
                    or expected_type in (int, (int, float))
                    and isinstance(value, bool)
                ):
                    type_name = (
                        "number"
                        if expected_type == (int, float)
                        else "integer"
                        if expected_type is int
                        else expected_type.__name__
                    )
                    errors.append(f"real report metadata {section}.{field} must be {type_name}")
                elif isinstance(value, str) and not value.strip():
                    errors.append(f"real report metadata {section}.{field} must be non-empty")

    platform_obj = report.get("platform", {})
    for field in ("name", "revision", "source_tree_sha", "host", "host_system"):
        if not isinstance(platform_obj.get(field), str):
            errors.append(f"report.platform.{field} must be string")

    for index, result in enumerate(report.get("results", [])):
        prefix = f"report.results[{index}]"
        if not isinstance(result, dict):
            errors.append(f"{prefix} must be object")
            continue
        for field, expected_type in REQUIRED_RESULT_FIELDS.items():
            if field not in result:
                errors.append(f"{prefix} missing {field}")
            elif not isinstance(result[field], expected_type):
                errors.append(f"{prefix}.{field} must be {expected_type.__name__}")
        status = result.get("status")
        for field, expected_type in STRICT_RESULT_METADATA_FIELDS.items():
            if field not in result:
                errors.append(f"{prefix} missing {field}")
            elif not isinstance(result[field], expected_type):
                errors.append(f"{prefix}.{field} must be {expected_type.__name__}")
        if result.get("parser") not in VALID_PARSERS:
            errors.append(f"{prefix}.parser is not supported")
        if result.get("provenance") not in VALID_PROVENANCE:
            errors.append(f"{prefix}.provenance is not supported")
        if status not in VALID_RESULT_STATUSES:
            errors.append(f"{prefix}.status {status!r} is not valid")
        if report.get("dry_run") is True and status == "passed":
            errors.append(f"{prefix} dry-run report must not contain passed results")
        if report.get("dry_run") is True and result.get("provenance") != "dry_run":
            errors.append(f"{prefix} dry-run result provenance must be dry_run")
        if report.get("dry_run") is False and status == "passed":
            if result.get("provenance") == "dry_run":
                errors.append(f"{prefix} real passed result cannot use dry_run provenance")
            if not isinstance(result.get("metrics"), dict) or not result["metrics"]:
                errors.append(f"{prefix} passed result missing parsed metrics")
            if not isinstance(result.get("run_metadata"), dict):
                errors.append(f"{prefix} passed result missing run_metadata")
            if isinstance(result.get("metrics"), dict) and isinstance(result.get("run_metadata"), dict):
                for error in check_metric_requirements(result["metrics"], result["run_metadata"]):
                    errors.append(f"{prefix}.metrics {error}")
                for error in check_calibration_requirements(report, result):
                    errors.append(f"{prefix}.calibration {error}")
        if status == "passed":
            if result.get("missing_dependencies"):
                errors.append(f"{prefix} passed with missing_dependencies")
            if result.get("blocked_assets"):
                errors.append(f"{prefix} passed with blocked_assets")
            for dep in result.get("dependencies", []):
                if dep.get("kind") == "model_artifact" and not dep.get("available"):
                    errors.append(f"{prefix} passed with unavailable model artifact {dep.get('name')}")
        if status == "blocked" and not (
            result.get("blocked_assets") or result.get("blocked_requirements") or result.get("missing_dependencies")
        ):
            errors.append(f"{prefix} blocked without blocked_assets, blocked_requirements, or missing_dependencies")
        if result.get("provenance") == "simulator":
            metrics = result.get("metrics", {})
            if isinstance(metrics, dict):
                for forbidden in ("wall_clock_score", "phone_score", "geekbench_score"):
                    if forbidden in metrics:
                        errors.append(f"{prefix}.metrics contains simulator-forbidden key {forbidden}")
            if report.get("claim_level") not in {"L0_RTL_UNIT", "L1_RTL_FULL_SOC", "L2_ARCH_SIM"}:
                errors.append(f"{prefix} simulator provenance is incompatible with {report.get('claim_level')}")
            if status == "passed":
                metrics = result.get("metrics", {})
                if isinstance(metrics, dict) and metrics.get("benchmark_success_allowed") is not True:
                    errors.append(f"{prefix}.metrics simulator benchmark_success_allowed must be true")
        for asset_index, asset in enumerate(result.get("blocked_assets", [])):
            asset_prefix = f"{prefix}.blocked_assets[{asset_index}]"
            if not isinstance(asset.get("blocker_id"), str) or not asset.get("blocker_id"):
                errors.append(f"{asset_prefix}.blocker_id must be non-empty string")
            for field in ("pipeline_visible", "release_blocking"):
                if not isinstance(asset.get(field), bool):
                    errors.append(f"{asset_prefix}.{field} must be bool")
        if not all(isinstance(part, str) for part in result.get("command", [])):
            errors.append(f"{prefix}.command must contain only strings")
        for dep_index, dep in enumerate(result.get("dependencies", [])):
            dep_prefix = f"{prefix}.dependencies[{dep_index}]"
            for field in ("name", "kind", "available"):
                if field not in dep:
                    errors.append(f"{dep_prefix} missing {field}")
            if "available" in dep and not isinstance(dep["available"], bool):
                errors.append(f"{dep_prefix}.available must be bool")
    return errors


def validate_report_file(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        report = json.load(f)
    return validate_report(report)


def run_benchmark(
    bench: dict[str, Any],
    args: argparse.Namespace,
    root: Path,
    run_dir: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    command = bench["command"]
    statuses = dependency_status(bench, root)
    missing = missing_dependencies(statuses)
    dependency_blockers = missing_dependency_blockers(bench, statuses)
    blocked = blocked_assets(statuses)
    blocked_requirements = []
    if not args.dry_run:
        blocked_requirements.extend(dependency_blockers)
        blocked_requirements.extend(metadata_blockers(report, bench))
    log_path = run_dir / f"{bench['name']}.log"
    result: dict[str, Any] = {
        "name": bench["name"],
        "suite": bench.get("suite", bench["name"]),
        "version": bench.get("version", "unknown"),
        "command": command,
        "input_dataset": bench.get("input_dataset", "none"),
        "primary_metric": bench.get("primary_metric", "not_parsed"),
        "units": bench.get("units", "unknown"),
        "parser": bench["parser"],
        "provenance": "dry_run" if args.dry_run else bench.get("provenance", "measured"),
        "dependencies": statuses,
        "artifacts": {"raw_output": str(log_path)},
    }

    if args.dry_run:
        result["status"] = "blocked" if blocked else "planned_missing_deps" if missing else "planned"
        result["missing_dependencies"] = missing
        if dependency_blockers:
            result["blocked_requirements"] = dependency_blockers
        if blocked:
            result["blocked_assets"] = blocked
        log_path.write_text("dry-run: command was not executed\n", encoding="utf-8")
        return result

    if blocked or blocked_requirements:
        result["status"] = "blocked"
        result["missing_dependencies"] = missing
        if blocked:
            result["blocked_assets"] = blocked
        if blocked_requirements:
            result["blocked_requirements"] = blocked_requirements
        lines = ["blocked benchmark requirements:"]
        lines.extend(f"- {item['name']}: {item['reason']}; {item.get('resolution', '')}" for item in blocked_requirements)
        lines.extend(f"- {item['name']}: {item['reason']}; {item.get('resolution', '')}" for item in blocked)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result

    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=bench.get("timeout_seconds", args.timeout_seconds),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        log_path.write_text(output + "\nTIMEOUT\n", encoding="utf-8")
        result.update({"status": "timeout", "elapsed_seconds": elapsed})
        return result
    except OSError as exc:
        result.update({"status": "error", "error": str(exc)})
        log_path.write_text(str(exc) + "\n", encoding="utf-8")
        return result

    elapsed = time.monotonic() - started
    log_path.write_text(completed.stdout, encoding="utf-8")
    result.update({"returncode": completed.returncode, "elapsed_seconds": elapsed})
    if completed.returncode != 0:
        result["status"] = "failed"
        return result
    try:
        result["metrics"] = parse_metrics(bench["parser"], completed.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        result.update({"status": "failed", "error": "parser failed: " + str(exc)})
        return result
    result["run_metadata"] = {
        "runs": int(bench.get("runs", 1)),
        "warmup_runs": int(bench.get("warmup_runs", 0)),
        "required_metadata": bench.get("required_metadata", list(REAL_METADATA_SECTIONS)),
        "required_metrics": bench.get("required_metrics", []),
        "metric_gates": bench.get("metric_gates", []),
        "required_calibration_assets": bench.get("required_calibration_assets", []),
    }
    metric_errors = check_metric_requirements(result["metrics"], result["run_metadata"])
    if metric_errors:
        result.update({"status": "failed", "error": "metric gate failed: " + "; ".join(metric_errors)})
        return result
    result["status"] = "passed"
    return result


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bench", action="append", default=[], help="Benchmark name; repeat or use all")
    parser.add_argument("--strict-missing", action="store_true", help="Return non-zero if dependencies are missing or blocked")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--report-id", default="manual")
    parser.add_argument("--platform", default="openphone-unknown")
    parser.add_argument("--platform-revision", default="unknown")
    parser.add_argument("--claim-level", default="L2_ARCH_SIM", choices=sorted(VALID_CLAIM_LEVELS))
    parser.add_argument("--metadata", type=Path, help="JSON file with software/clocks/memory/thermal/power metadata for real runs")


def parse_args(argv: list[str]) -> argparse.Namespace:
    normalized = list(argv)
    if not normalized or normalized[0] not in COMMANDS:
        normalized.insert(0, "run")

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List configured benchmarks and dependency hints")
    list_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    plan_parser = subparsers.add_parser("plan", help="Create a dry-run report without executing commands")
    add_common_args(plan_parser)

    run_parser = subparsers.add_parser("run", help="Execute benchmarks whose dependencies and assets are available")
    add_common_args(run_parser)
    run_parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)

    validate_parser = subparsers.add_parser("validate-report", help="Validate a generated report JSON file")
    validate_parser.add_argument("report", type=Path)
    return parser.parse_args(normalized)


def print_benchmark_list(config: dict[str, Any]) -> None:
    for bench in config["benchmarks"]:
        print(f"{bench['name']}: {bench['suite']} ({bench.get('version', 'unknown')})")
        print("  command: " + " ".join(bench["command"]))
        if bench.get("requires"):
            print("  tools: " + ", ".join(bench["requires"]))
        if bench.get("required_files"):
            print("  files: " + ", ".join(bench["required_files"]))
        if bench.get("model_artifacts"):
            print("  model artifacts: " + ", ".join(asset["path"] for asset in bench["model_artifacts"]))
            for asset in bench["model_artifacts"]:
                if asset.get("generator"):
                    print("  model generator: " + " ".join(asset["generator"]["command"]))
        if bench.get("install"):
            print("  install: " + bench["install"])


def run_plan_or_real(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.command == "plan":
        args = copy.copy(args)
        args.dry_run = True
    elif not hasattr(args, "dry_run"):
        args.dry_run = False
    config_path = args.config if args.config.is_absolute() else root / args.config
    out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir

    config = load_config(config_path)
    benches = selected_benchmarks(config, set(args.bench))
    run_dir = out_dir / args.report_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report = base_report(args, config, root)
    any_missing = False
    any_blocked = False
    any_failed = False
    for bench in benches:
        result = run_benchmark(bench, args, root, run_dir, report)
        report["results"].append(result)
        any_missing = any_missing or bool(result.get("missing_dependencies"))
        any_blocked = any_blocked or bool(result.get("blocked_assets")) or bool(result.get("blocked_requirements"))
        any_failed = any_failed or result["status"] in {"failed", "timeout", "error"}

        status = result["status"]
        command = " ".join(result["command"])
        print(f"{bench['name']}: {status}: {command}")
        if result.get("missing_dependencies"):
            print("  missing: " + ", ".join(result["missing_dependencies"]))
        if result.get("blocked_assets"):
            print("  blocked: " + ", ".join(f"{item['name']} ({item['reason']})" for item in result["blocked_assets"]))
        if result.get("blocked_requirements"):
            print(
                "  blocked requirements: "
                + ", ".join(f"{item['name']} ({item['reason']})" for item in result["blocked_requirements"])
            )

    errors = validate_report(report)
    if errors:
        for error in errors:
            print(f"schema error: {error}", file=sys.stderr)
        return 3

    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {display_path(report_path, root)}")

    if any_failed:
        return 1
    if (any_missing or any_blocked) and args.strict_missing:
        return 2
    return 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = repo_root()
    if args.command == "validate-report":
        report_path = args.report if args.report.is_absolute() else root / args.report
        errors = validate_report_file(report_path)
        if errors:
            for error in errors:
                print(f"schema error: {error}", file=sys.stderr)
            return 3
        print(f"{report_path}: valid")
        return 0
    if args.command == "list":
        config_path = args.config if args.config.is_absolute() else root / args.config
        print_benchmark_list(load_config(config_path))
        return 0
    return run_plan_or_real(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
