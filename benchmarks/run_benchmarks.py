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
        if not isinstance(bench["command"], list) or not all(isinstance(part, str) for part in bench["command"]):
            raise ValueError(f"{location} command must be a list of strings")
        for list_key in ("requires", "required_files", "model_artifacts"):
            if list_key in bench and not isinstance(bench[list_key], list):
                raise ValueError(f"{location} {list_key} must be a list")
        for asset in bench.get("model_artifacts", []):
            if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
                raise ValueError(f"{location} model_artifacts entries must contain a string path")


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
    }
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


def blocked_assets(statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"name": item["name"], "reason": item.get("blocked_reason", "unavailable_model_artifact")}
        for item in statuses
        if not item["available"] and item.get("kind") == "model_artifact"
    ]


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
        if status == "passed":
            if result.get("missing_dependencies"):
                errors.append(f"{prefix} passed with missing_dependencies")
            if result.get("blocked_assets"):
                errors.append(f"{prefix} passed with blocked_assets")
            for dep in result.get("dependencies", []):
                if dep.get("kind") == "model_artifact" and not dep.get("available"):
                    errors.append(f"{prefix} passed with unavailable model artifact {dep.get('name')}")
        if status == "blocked" and not result.get("blocked_assets"):
            errors.append(f"{prefix} blocked without blocked_assets")
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
    statuses = dependency_status(bench, root)
    missing = missing_dependencies(statuses)
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

    if args.dry_run:
        result["status"] = "blocked" if blocked else "planned_missing_deps" if missing else "planned"
        result["missing_dependencies"] = missing
        if blocked:
            result["blocked_assets"] = blocked
        log_path.write_text("dry-run: command was not executed\n", encoding="utf-8")
        return result

    if blocked:
        result["status"] = "blocked"
        result["missing_dependencies"] = missing
        result["blocked_assets"] = blocked
        lines = ["blocked model artifacts:"]
        lines.extend(f"- {item['name']}: {item['reason']}" for item in blocked)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result

    if missing:
        result["status"] = "missing_dependencies"
        result["missing_dependencies"] = missing
        log_path.write_text(
            "missing dependencies:\n" + "\n".join(f"- {dep}" for dep in missing) + "\n",
            encoding="utf-8",
        )
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
    result.update(
        {
            "status": "passed" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
        }
    )
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
        if result.get("blocked_assets"):
            print("  blocked: " + ", ".join(f"{item['name']} ({item['reason']})" for item in result["blocked_assets"]))

    errors = validate_report(report)
    if errors:
        for error in errors:
            print(f"schema error: {error}", file=sys.stderr)
        return 3

    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {report_path.relative_to(root)}")

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
