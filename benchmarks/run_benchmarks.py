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
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
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
LOCAL_TOOL_DIRS = ("tools/bin", ".venv/bin")
HOST_SMOKE_TOOL_DIR = "benchmarks/tools"
HOST_SMOKE_MARKER = "openphone-host-smoke"
HOST_SMOKE_CLAIM_LEVEL = "L2_ARCH_SIM"
EXECUTABLE_MARKER_READ_BYTES = 256 * 1024
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


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def is_json_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
        for key in ("name", "suite", "version", "command", "primary_metric", "units"):
            if key not in bench:
                raise ValueError(f"{location} missing required key {key!r}")
        if not isinstance(bench["name"], str) or not bench["name"]:
            raise ValueError(f"{location} name must be a non-empty string")
        if bench["name"] in names:
            raise ValueError(f"{location} duplicate benchmark name {bench['name']!r}")
        names.add(bench["name"])
        if not isinstance(bench["command"], list) or not all(
            isinstance(part, str) for part in bench["command"]
        ):
            raise ValueError(f"{location} command must be a list of strings")
        for list_key in ("requires", "required_files", "model_artifacts", "capability_artifacts"):
            if list_key in bench and not isinstance(bench[list_key], list):
                raise ValueError(f"{location} {list_key} must be a list")
        for asset in bench.get("model_artifacts", []) + bench.get("capability_artifacts", []):
            if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
                raise ValueError(f"{location} artifact entries must contain a string path")
            for bool_key in ("pipeline_visible", "release_blocking"):
                if bool_key in asset and not isinstance(asset[bool_key], bool):
                    raise ValueError(f"{location} model_artifacts {bool_key} must be a boolean")
            if (
                asset.get("placeholder_allowed") is True
                and asset.get("release_blocking", True) is True
            ):
                raise ValueError(
                    f"{location} release-blocking model artifacts must not allow placeholders"
                )
            if "generator" in asset:
                generator = asset["generator"]
                if not isinstance(generator, dict) or not isinstance(
                    generator.get("command"), list
                ):
                    raise ValueError(f"{location} model_artifacts generator.command must be a list")
                if not all(isinstance(part, str) for part in generator["command"]):
                    raise ValueError(
                        f"{location} model_artifacts generator.command must contain strings"
                    )
            if "proof" in asset:
                proof = asset["proof"]
                if not isinstance(proof, dict):
                    raise ValueError(f"{location} capability proof must be an object")
                if proof.get("schema") and not isinstance(proof["schema"], str):
                    raise ValueError(f"{location} capability proof.schema must be a string")
                if proof.get("accelerator_name") and not isinstance(proof["accelerator_name"], str):
                    raise ValueError(
                        f"{location} capability proof.accelerator_name must be a string"
                    )
                if proof.get("required_files") and not isinstance(proof["required_files"], list):
                    raise ValueError(f"{location} capability proof.required_files must be a list")
                if proof.get("required_model_artifacts") and not isinstance(
                    proof["required_model_artifacts"], list
                ):
                    raise ValueError(
                        f"{location} capability proof.required_model_artifacts must be a list"
                    )
                for model_path in proof.get("required_model_artifacts", []):
                    if not isinstance(model_path, str) or not model_path:
                        raise ValueError(
                            f"{location} capability proof.required_model_artifacts entries must be non-empty strings"
                        )
                if proof.get("max_cpu_fallback_percent") is not None and not is_json_number(
                    proof["max_cpu_fallback_percent"]
                ):
                    raise ValueError(
                        f"{location} capability proof.max_cpu_fallback_percent must be numeric"
                    )
                if proof.get("max_unsupported_op_count") is not None and (
                    not isinstance(proof["max_unsupported_op_count"], int)
                    or isinstance(proof["max_unsupported_op_count"], bool)
                ):
                    raise ValueError(
                        f"{location} capability proof.max_unsupported_op_count must be an integer"
                    )
                markers = proof.get("required_transcript_markers")
                if markers is not None:
                    if not isinstance(markers, dict):
                        raise ValueError(
                            f"{location} capability proof.required_transcript_markers must be an object"
                        )
                    for name, values in markers.items():
                        if not isinstance(name, str) or not name:
                            raise ValueError(
                                f"{location} capability proof.required_transcript_markers keys must be strings"
                            )
                        if not isinstance(values, list) or not all(
                            isinstance(value, str) and value for value in values
                        ):
                            raise ValueError(
                                f"{location} capability proof.required_transcript_markers values must be non-empty string lists"
                            )


def source_tree_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=root,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def local_search_path(root: Path, include_host_smoke: bool = False) -> str:
    local_dirs = [str(root / path) for path in LOCAL_TOOL_DIRS if (root / path).is_dir()]
    env_dirs = [
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and Path(entry).resolve() != (root / HOST_SMOKE_TOOL_DIR).resolve()
    ]
    smoke_dirs = (
        [str(root / HOST_SMOKE_TOOL_DIR)]
        if include_host_smoke and (root / HOST_SMOKE_TOOL_DIR).is_dir()
        else []
    )
    return os.pathsep.join(local_dirs + env_dirs + smoke_dirs)


def is_host_smoke_tool(path: str | None, root: Path) -> bool:
    if not path:
        return False
    resolved = Path(path).resolve()
    smoke_dir = (root / HOST_SMOKE_TOOL_DIR).resolve()
    try:
        resolved.relative_to(smoke_dir)
        return True
    except ValueError:
        pass
    try:
        with resolved.open("rb") as f:
            return HOST_SMOKE_MARKER.encode("utf-8") in f.read(EXECUTABLE_MARKER_READ_BYTES)
    except OSError:
        return False


def executable_metadata(path: str | None, root: Path, allow_host_smoke: bool) -> dict[str, Any]:
    if not path:
        return {}
    resolved = Path(path)
    metadata: dict[str, Any] = {
        "evidence_kind": "host_smoke_tool"
        if is_host_smoke_tool(str(resolved), root)
        else "executable",
    }
    try:
        metadata["sha256"] = sha256_file(resolved)
        metadata["size_bytes"] = resolved.stat().st_size
    except OSError:
        pass
    if metadata["evidence_kind"] == "host_smoke_tool":
        metadata["provenance"] = "repo_local_host_smoke"
        metadata["release_claim_allowed"] = False
    else:
        metadata["provenance"] = "path_executable"
        metadata["release_claim_allowed"] = True
    metadata["host_smoke_allowed_for_run"] = allow_host_smoke
    return metadata


def command_available(
    executable: str,
    root: Path,
    allow_host_smoke: bool = False,
) -> tuple[bool, str | None, str | None, list[dict[str, str]]]:
    candidate = Path(executable)
    if candidate.parts and (candidate.is_absolute() or len(candidate.parts) > 1):
        resolved_path = candidate if candidate.is_absolute() else root / candidate
        available = resolved_path.exists() and os.access(resolved_path, os.X_OK)
        reason = (
            "repo_local_host_smoke_tool"
            if available and is_host_smoke_tool(str(resolved_path), root)
            else None
        )
        if allow_host_smoke and reason == "repo_local_host_smoke_tool":
            reason = None
        return available and reason is None, str(resolved_path), reason, []

    first_smoke_match: str | None = None
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in local_search_path(root, include_host_smoke=allow_host_smoke).split(os.pathsep):
        if not entry:
            continue
        resolved = shutil.which(executable, path=entry)
        if resolved is None:
            continue
        resolved_key = str(Path(resolved).resolve())
        if resolved_key in seen:
            continue
        seen.add(resolved_key)
        if is_host_smoke_tool(resolved, root):
            if allow_host_smoke:
                return True, resolved, None, rejected
            first_smoke_match = first_smoke_match or resolved
            rejected.append({"path": resolved, "reason": "repo_local_host_smoke_tool"})
            continue
        return True, resolved, None, rejected

    if first_smoke_match is None:
        first_smoke_match = shutil.which(
            executable, path=local_search_path(root, include_host_smoke=True)
        )
    reason = "repo_local_host_smoke_tool" if first_smoke_match else None
    return False, first_smoke_match, reason, rejected


def benchmark_env(root: Path, allow_host_smoke: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = local_search_path(root, include_host_smoke=allow_host_smoke)
    return env


def dependency_status(
    bench: dict[str, Any], root: Path, allow_host_smoke: bool = False
) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for dep in bench.get("requires", []):
        ok, resolved, blocked_reason, rejected = command_available(
            dep, root, allow_host_smoke=allow_host_smoke
        )
        status = {"name": dep, "kind": "executable", "available": ok, "path": resolved}
        status.update(executable_metadata(resolved, root, allow_host_smoke=allow_host_smoke))
        if rejected:
            status["rejected_candidates"] = rejected
        if blocked_reason:
            status.update(
                {
                    "blocked_reason": blocked_reason,
                    "resolution": bench.get("install", f"Install a real {dep} executable on PATH."),
                }
            )
        statuses.append(status)
    for artifact in bench.get("required_files", []):
        path = root / artifact
        statuses.append(
            {"name": artifact, "kind": "file", "available": path.is_file(), "path": str(path)}
        )
    for artifact in bench.get("model_artifacts", []):
        statuses.append(model_artifact_status(artifact, root))
    for artifact in bench.get("capability_artifacts", []):
        statuses.append(capability_artifact_status(artifact, root))
    return statuses


def command_with_resolved_executable(
    command: list[str], statuses: list[dict[str, Any]]
) -> list[str]:
    if not command:
        return command
    executable = command[0]
    for item in statuses:
        if (
            item.get("kind") == "executable"
            and item.get("name") == executable
            and item.get("available")
            and item.get("path")
        ):
            return [str(item["path"]), *command[1:]]
    return command


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


def capability_artifact_status(artifact: dict[str, Any], root: Path) -> dict[str, Any]:
    path = root / artifact["path"]
    status = {
        "name": artifact["path"],
        "kind": "capability_artifact",
        "available": path.is_file(),
        "path": str(path),
        "blocker_id": artifact.get("blocker_id", "CAPABILITY_ARTIFACT_UNAVAILABLE"),
        "pipeline_visible": bool(artifact.get("pipeline_visible", True)),
        "release_blocking": bool(artifact.get("release_blocking", True)),
        "resolution": artifact.get("resolution", ""),
        **(
            {}
            if path.is_file()
            else {"blocked_reason": artifact.get("blocked_reason", "missing_capability_artifact")}
        ),
    }
    proof = artifact.get("proof")
    if not path.is_file() or not proof:
        return status

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        status["available"] = False
        status["blocked_reason"] = "invalid_capability_proof"
        status["error"] = str(exc)
        return status

    errors: list[str] = []
    expected_schema = proof.get("schema")
    if expected_schema and data.get("schema") != expected_schema:
        errors.append(f"schema must be {expected_schema}")
    expected_accelerator = proof.get("accelerator_name")
    if expected_accelerator and data.get("accelerator_name") != expected_accelerator:
        errors.append(f"accelerator_name must be {expected_accelerator}")
    for field in ("target", "generated_by", "date_utc"):
        if not isinstance(data.get(field), str) or not data[field]:
            errors.append(f"{field} must be a non-empty string")

    nnapi = data.get("nnapi")
    if not isinstance(nnapi, dict):
        errors.append("nnapi must be an object")
    else:
        if expected_accelerator and nnapi.get("accelerator_name") != expected_accelerator:
            errors.append(f"nnapi.accelerator_name must be {expected_accelerator}")
        fallback_percent = nnapi.get("cpu_fallback_percent")
        max_fallback = proof.get("max_cpu_fallback_percent")
        if not is_json_number(fallback_percent):
            errors.append("nnapi.cpu_fallback_percent must be numeric")
        elif max_fallback is not None and fallback_percent > max_fallback:
            errors.append(
                f"nnapi.cpu_fallback_percent must be <= {max_fallback}; got {fallback_percent}"
            )
        unsupported_ops = nnapi.get("unsupported_op_count")
        max_unsupported = proof.get("max_unsupported_op_count")
        if not isinstance(unsupported_ops, int) or isinstance(unsupported_ops, bool):
            errors.append("nnapi.unsupported_op_count must be an integer")
        elif max_unsupported is not None and unsupported_ops > max_unsupported:
            errors.append(
                f"nnapi.unsupported_op_count must be <= {max_unsupported}; got {unsupported_ops}"
            )

    model_artifacts = data.get("model_artifacts")
    required_models = proof.get("required_model_artifacts", [])
    if required_models and not isinstance(model_artifacts, dict):
        errors.append("model_artifacts must be an object")
    elif isinstance(model_artifacts, dict):
        for model_path in required_models:
            model_entry = model_artifacts.get(model_path)
            if not isinstance(model_entry, dict):
                errors.append(f"model_artifacts.{model_path} must be an object")
                continue
            recorded_sha = model_entry.get("sha256")
            if not isinstance(recorded_sha, str) or not re.fullmatch(
                r"[0-9a-fA-F]{64}", recorded_sha
            ):
                errors.append(f"model_artifacts.{model_path}.sha256 must be a SHA-256 hex string")
                continue
            local_model = root / model_path
            if not local_model.is_file():
                errors.append(f"model artifact {model_path} is missing")
                continue
            actual_sha = sha256_file(local_model)
            if recorded_sha.lower() != actual_sha:
                errors.append(
                    f"model_artifacts.{model_path}.sha256 does not match current repository file"
                )

    transcript = data.get("transcripts")
    transcript_paths: dict[str, Path] = {}
    if not isinstance(transcript, dict) or not transcript:
        errors.append("transcripts must be a non-empty object")
    else:
        for name in proof.get("required_files", []):
            rel = transcript.get(name)
            if not isinstance(rel, str) or not rel:
                errors.append(f"transcripts.{name} must name a non-empty file")
                continue
            transcript_path = root / rel
            if not transcript_path.is_file() or transcript_path.stat().st_size == 0:
                errors.append(f"transcript {rel} is missing or empty")
                continue
            transcript_paths[name] = transcript_path

    for name, markers in proof.get("required_transcript_markers", {}).items():
        marker_transcript_path = transcript_paths.get(name)
        if marker_transcript_path is None:
            continue
        try:
            text = marker_transcript_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(
                f"transcript {marker_transcript_path.relative_to(root)} could not be read: {exc}"
            )
            continue
        for marker in markers:
            if marker not in text:
                errors.append(
                    f"transcript {transcript_path.relative_to(root)} must contain {marker!r}"
                )

    if errors:
        status["available"] = False
        status["blocked_reason"] = "invalid_capability_proof"
        status["errors"] = errors
    else:
        status["proof_schema"] = data.get("schema")
        status["target"] = data.get("target")
        status["accelerator_name"] = data.get("accelerator_name")
        status["transcript_sha256"] = {
            name: sha256_file(path) for name, path in sorted(transcript_paths.items())
        }
    return status


def missing_dependencies(statuses: list[dict[str, Any]]) -> list[str]:
    return [
        item["name"]
        for item in statuses
        if not item["available"]
        and item.get("kind") not in {"model_artifact", "capability_artifact"}
    ]


def missing_dependency_details(statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details = []
    for item in statuses:
        if item["available"] or item.get("kind") in {"model_artifact", "capability_artifact"}:
            continue
        details.append(
            {
                "name": item["name"],
                "kind": item.get("kind", "unknown"),
                "reason": item.get("blocked_reason", "missing_dependency"),
                "path": item.get("path"),
                "resolution": item.get("resolution", ""),
            }
        )
    return details


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
        if not item["available"] and item.get("kind") in {"model_artifact", "capability_artifact"}
    ]


def parse_metrics(bench: dict[str, Any], output: str) -> tuple[str | None, dict[str, Any]]:
    name = bench["name"]
    if name == "coremark":
        required = re.search(r"Iterations/Sec\s*:\s*([0-9]+(?:\.[0-9]+)?)", output)
        if not required:
            return None, {}
        metrics = {"iterations_per_second": float(required.group(1))}
        match = re.search(r"CoreMark\s*/\s*MHz\s*:\s*([0-9]+(?:\.[0-9]+)?)", output)
        if match:
            metrics["coremark_per_mhz"] = float(match.group(1))
        return "coremark_v1", metrics

    if name == "stream":
        metrics = {}
        for kernel in ("Copy", "Scale", "Add", "Triad"):
            match = re.search(rf"^\s*{kernel}\s*:\s*([0-9]+(?:\.[0-9]+)?)", output, re.MULTILINE)
            if match:
                metrics[f"{kernel.lower()}_mb_per_s"] = float(match.group(1))
        return ("stream_v1", metrics) if "triad_mb_per_s" in metrics else (None, {})

    if name == "lmbench_bw_mem":
        last = None
        for match in re.finditer(
            r"^\s*([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)\s*$", output, re.MULTILINE
        ):
            last = match
        if not last:
            return None, {}
        return "lmbench_bw_mem_v1", {
            "size_mb": float(last.group(1)),
            "bandwidth_mb_per_s": float(last.group(2)),
        }

    if name == "lmbench_lat_mem_rd":
        points = [
            (float(match.group(1)), float(match.group(2)))
            for match in re.finditer(
                r"^\s*([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)\s*$", output, re.MULTILINE
            )
        ]
        if not points:
            return None, {}
        latencies = [lat for _, lat in points]
        return "lmbench_lat_mem_rd_v1", {
            "points": len(points),
            "min_latency_ns": min(latencies),
            "max_latency_ns": max(latencies),
        }

    if name.startswith("fio_"):
        try:
            start = output.find("{")
            data = json.loads(output[start:] if start >= 0 else output)
        except json.JSONDecodeError:
            return None, {}
        jobs = data.get("jobs") or []
        if not jobs:
            return None, {}
        read_iops = sum(float(job.get("read", {}).get("iops", 0.0)) for job in jobs)
        write_iops = sum(float(job.get("write", {}).get("iops", 0.0)) for job in jobs)
        read_bw = sum(float(job.get("read", {}).get("bw", 0.0)) for job in jobs)
        write_bw = sum(float(job.get("write", {}).get("bw", 0.0)) for job in jobs)
        return "fio_json_v1", {
            "jobs": len(jobs),
            "read_iops": read_iops,
            "write_iops": write_iops,
            "read_bw_kib_s": read_bw,
            "write_bw_kib_s": write_bw,
        }

    if name.startswith("tflite_"):
        match = re.search(
            r"Inference timings in us:\s*Init:\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*"
            r"First inference:\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*"
            r"Warmup\s*\(avg\):\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*"
            r"Inference\s*\(avg\):\s*([0-9]+(?:\.[0-9]+)?)",
            output,
        )
        if not match:
            return None, {}
        metrics = {
            "init_us": float(match.group(1)),
            "first_inference_us": float(match.group(2)),
            "warmup_avg_us": float(match.group(3)),
            "avg_latency_us": float(match.group(4)),
        }
        delegated = re.search(
            r"NNAPI delegated\s+([0-9]+)\s+nodes;\s+([0-9]+)\s+fallback to CPU", output
        )
        if delegated:
            metrics["nnapi_delegated_nodes"] = int(delegated.group(1))
            metrics["cpu_fallback_nodes"] = int(delegated.group(2))
        unsupported = re.search(r"Number of unsupported ops:\s*([0-9]+)", output)
        if unsupported:
            metrics["unsupported_op_count"] = int(unsupported.group(1))
        return "tflite_benchmark_model_v1", metrics

    return None, {}


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
    return {
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
        if status not in VALID_RESULT_STATUSES:
            errors.append(f"{prefix}.status {status!r} is not valid")
        if report.get("dry_run") is True and status == "passed":
            errors.append(f"{prefix} dry-run report must not contain passed results")
        if status == "passed":
            if result.get("missing_dependencies"):
                errors.append(f"{prefix} passed with missing_dependencies")
            if result.get("blocked_assets"):
                errors.append(f"{prefix} passed with blocked_assets")
            for dep in result.get("dependencies", []):
                if dep.get("kind") in {"model_artifact", "capability_artifact"} and not dep.get(
                    "available"
                ):
                    errors.append(
                        f"{prefix} passed with unavailable {dep.get('kind')} {dep.get('name')}"
                    )
                if (
                    report.get("claim_level") != HOST_SMOKE_CLAIM_LEVEL
                    and dep.get("release_claim_allowed") is False
                ):
                    errors.append(
                        f"{prefix} {report.get('claim_level')} passed with non-release dependency {dep.get('name')}"
                    )
        if status == "blocked" and not result.get("blocked_assets"):
            errors.append(f"{prefix} blocked without blocked_assets")
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
) -> dict[str, Any]:
    command = bench["command"]
    statuses = dependency_status(bench, root, allow_host_smoke=args.allow_host_smoke_tools)
    execution_command = command_with_resolved_executable(command, statuses)
    missing = missing_dependencies(statuses)
    missing_details = missing_dependency_details(statuses)
    blocked = blocked_assets(statuses)
    log_path = run_dir / f"{bench['name']}.log"
    result: dict[str, Any] = {
        "name": bench["name"],
        "suite": bench.get("suite", bench["name"]),
        "version": bench.get("version", "unknown"),
        "command": command,
        "input_dataset": bench.get("input_dataset", "none"),
        "primary_metric": bench.get("primary_metric", "not_parsed"),
        "units": bench.get("units", "unknown"),
        "dependencies": statuses,
        "artifacts": {"raw_output": str(log_path)},
    }
    if execution_command != command:
        result["resolved_command"] = execution_command

    if args.dry_run:
        result["status"] = (
            "blocked" if blocked else "planned_missing_deps" if missing else "planned"
        )
        result["missing_dependencies"] = missing
        if missing_details:
            result["missing_dependency_details"] = missing_details
        if blocked:
            result["blocked_assets"] = blocked
        log_path.write_text("dry-run: command was not executed\n", encoding="utf-8")
        return result

    if blocked:
        result["status"] = "blocked"
        result["missing_dependencies"] = missing
        if missing_details:
            result["missing_dependency_details"] = missing_details
        result["blocked_assets"] = blocked
        lines = ["blocked model artifacts:"]
        lines.extend(f"- {item['name']}: {item['reason']}" for item in blocked)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result

    if missing:
        result["status"] = "missing_dependencies"
        result["missing_dependencies"] = missing
        if missing_details:
            result["missing_dependency_details"] = missing_details
        log_path.write_text(
            "missing dependencies:\n"
            + "\n".join(
                f"- {item['name']}: {item['reason']}"
                + (f" at {item['path']}" if item.get("path") else "")
                + (f"; {item['resolution']}" if item.get("resolution") else "")
                for item in missing_details
            )
            + "\n",
            encoding="utf-8",
        )
        return result

    started = time.monotonic()
    try:
        completed = subprocess.run(
            execution_command,
            cwd=root,
            env=benchmark_env(root, allow_host_smoke=args.allow_host_smoke_tools),
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
    parser_name, metrics = parse_metrics(bench, completed.stdout)
    result.update(
        {
            "status": "passed" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
        }
    )
    if parser_name:
        result["parser"] = parser_name
        result["metrics"] = metrics
        result["provenance"] = "measured"
    return result


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--bench", action="append", default=[], help="Benchmark name; repeat or use all"
    )
    parser.add_argument(
        "--strict-missing",
        action="store_true",
        help="Return non-zero if dependencies are missing or blocked",
    )
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--report-id", default="manual")
    parser.add_argument("--platform", default="openphone-unknown")
    parser.add_argument("--platform-revision", default="unknown")
    parser.add_argument("--claim-level", default="L2_ARCH_SIM", choices=sorted(VALID_CLAIM_LEVELS))
    parser.add_argument(
        "--allow-host-smoke-tools",
        action="store_true",
        help="Allow repo-local host smoke tools in benchmarks/tools for L2 developer evidence.",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    normalized = list(argv)
    if not normalized or normalized[0] not in COMMANDS:
        normalized.insert(0, "run")

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list", help="List configured benchmarks and dependency hints"
    )
    list_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    plan_parser = subparsers.add_parser(
        "plan", help="Create a dry-run report without executing commands"
    )
    add_common_args(plan_parser)

    run_parser = subparsers.add_parser(
        "run", help="Execute benchmarks whose dependencies and assets are available"
    )
    add_common_args(run_parser)
    run_parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)

    validate_parser = subparsers.add_parser(
        "validate-report", help="Validate a generated report JSON file"
    )
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
            print(
                "  model artifacts: "
                + ", ".join(asset["path"] for asset in bench["model_artifacts"])
            )
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
    if args.allow_host_smoke_tools and args.claim_level != HOST_SMOKE_CLAIM_LEVEL:
        print(
            f"--allow-host-smoke-tools is only valid with --claim-level {HOST_SMOKE_CLAIM_LEVEL}; "
            f"{args.claim_level} claims must use real benchmark executables.",
            file=sys.stderr,
        )
        return 2
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
        result = run_benchmark(bench, args, root, run_dir)
        report["results"].append(result)
        any_missing = any_missing or bool(result.get("missing_dependencies"))
        any_blocked = any_blocked or bool(result.get("blocked_assets"))
        any_failed = any_failed or result["status"] in {"failed", "timeout", "error"}

        status = result["status"]
        command = " ".join(result["command"])
        print(f"{bench['name']}: {status}: {command}")
        if result.get("missing_dependencies"):
            print("  missing: " + ", ".join(result["missing_dependencies"]))
        for item in result.get("missing_dependency_details", []):
            path = f" at {item['path']}" if item.get("path") else ""
            resolution = f"; {item['resolution']}" if item.get("resolution") else ""
            print(f"    - {item['name']}: {item['reason']}{path}{resolution}")
        if result.get("blocked_assets"):
            print(
                "  blocked: "
                + ", ".join(
                    f"{item['name']} ({item['reason']})" for item in result["blocked_assets"]
                )
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
