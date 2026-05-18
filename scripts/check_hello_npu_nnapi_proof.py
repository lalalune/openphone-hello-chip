#!/usr/bin/env python3
"""Check the hello-npu NNAPI capability proof gate.

This is a readiness and validation check, not a proof generator. It validates
the configured capability artifact when present and records concrete local
blockers when proof cannot be produced from this machine.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CAPTURE_COMMANDS = {
    "adb_devices": "adb devices",
    "nnapi_accelerator_query": "adb shell cmd neuralnetworks list",
    "benchmark_model_nnapi": (
        "adb shell benchmark_model --graph=/data/local/tmp/mobile_smoke.tflite "
        "--use_nnapi=true --nnapi_accelerator_name=hello-npu "
        "--enable_op_profiling=true --verbose=true"
    ),
    "dma_trace": "adb shell cat /sys/bus/platform/devices/10020000.npu/dma_trace",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("benchmarks/configs/benchmark_plan.json")
    )
    parser.add_argument(
        "--status-json", type=Path, help="Optional output path for the readiness JSON."
    )
    parser.add_argument(
        "--allow-host-smoke-tools",
        action="store_true",
        help="Include repo-local host smoke tools in dependency diagnostics.",
    )
    parser.add_argument(
        "--probe-adb",
        action="store_true",
        help="Run 'adb devices' if adb is installed and include the result in diagnostics.",
    )
    return parser.parse_args(argv)


def find_benchmark(config: dict[str, Any], name: str) -> dict[str, Any]:
    for bench in config["benchmarks"]:
        if bench["name"] == name:
            return bench
    raise ValueError(f"benchmark plan missing {name}")


def adb_probe() -> dict[str, Any]:
    adb = shutil.which("adb")
    status: dict[str, Any] = {
        "adb": adb,
        "status": "blocked",
        "devices": [],
    }
    if not adb:
        status["blocked_reason"] = "adb_not_installed"
        return status
    result = subprocess.run(
        [adb, "devices"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    )
    status["returncode"] = result.returncode
    status["stdout"] = result.stdout
    if result.returncode != 0:
        status["blocked_reason"] = "adb_devices_failed"
        return status
    devices = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    status["devices"] = devices
    if devices:
        status["status"] = "available"
        status.pop("blocked_reason", None)
    else:
        status["blocked_reason"] = "no_adb_device"
    return status


def main(argv: list[str]) -> int:
    root = repo_root()
    sys.path.insert(0, str(root))
    from benchmarks import run_benchmarks

    args = parse_args(argv)
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = run_benchmarks.load_config(config_path)
    bench = find_benchmark(config, "tflite_hello_npu")
    artifacts = bench.get("capability_artifacts", [])
    if len(artifacts) != 1:
        raise ValueError("tflite_hello_npu must have exactly one capability artifact")

    artifact_status = run_benchmarks.capability_artifact_status(artifacts[0], root)
    dependencies = run_benchmarks.dependency_status(
        bench,
        root,
        allow_host_smoke=args.allow_host_smoke_tools,
    )
    missing_details = run_benchmarks.missing_dependency_details(dependencies)
    blocked_assets = run_benchmarks.blocked_assets(dependencies)

    local_blockers: list[dict[str, Any]] = []
    if not artifact_status.get("available"):
        local_blockers.append(
            {
                "name": artifact_status["name"],
                "kind": artifact_status["kind"],
                "blocked_reason": artifact_status.get("blocked_reason", "unavailable"),
                "blocker_id": artifact_status.get("blocker_id"),
                "resolution": artifact_status.get("resolution", ""),
            }
        )
    for blocker in missing_details + blocked_assets:
        if blocker.get("name") != artifact_status["name"]:
            local_blockers.append(blocker)

    probe = adb_probe() if args.probe_adb else None
    if probe and probe.get("status") != "available":
        local_blockers.append(
            {
                "name": "adb_devices",
                "kind": "target_probe",
                "blocked_reason": probe.get("blocked_reason", "adb_unavailable"),
                "resolution": "Connect an Android target that exposes hello-npu over NNAPI.",
            }
        )

    real_tool_ready = not any(
        blocker.get("kind") == "executable" and blocker.get("name") == "benchmark_model"
        for blocker in missing_details
    )
    target_ready = bool(probe and probe.get("status") == "available")

    status = {
        "schema": "openphone.hello_npu_nnapi_proof_readiness.v1",
        "benchmark": "tflite_hello_npu",
        "status": "ready" if artifact_status.get("available") else "blocked",
        "proof_valid": bool(artifact_status.get("available")),
        "can_generate_locally": bool(real_tool_ready and target_ready),
        "proof_artifact": artifact_status,
        "dependencies": dependencies,
        "local_blockers": local_blockers,
        "adb_probe": probe,
        "required_capture_commands": CAPTURE_COMMANDS,
    }

    output = json.dumps(status, indent=2, sort_keys=True) + "\n"
    if args.status_json:
        status_path = (
            args.status_json if args.status_json.is_absolute() else root / args.status_json
        )
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if status["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
