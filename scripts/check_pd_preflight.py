#!/usr/bin/env python3
from pathlib import Path
import json
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [
    ROOT / "pd/openlane/config.json",
    ROOT / "pd/openlane/config.sky130.json",
    ROOT / "pd/openlane/config.gf180.json",
]
OPENLANE_IMAGE = "ghcr.io/efabless/openlane2:2.4.0.dev1"
OPENLANE_IMAGE_DIGEST = "sha256:bcaabac3b114dfb9e739af9f16b53a79ce1b744bcdb3ad4fc476c961581fe5d5"
REQUIRED_KEYS = {
    "DESIGN_NAME",
    "VERILOG_FILES",
    "CLOCK_PORT",
    "CLOCK_PERIOD",
}


def resolve_dir_path(config_path: Path, value: str) -> Path:
    if value.startswith("dir::"):
        return (config_path.parent / value.removeprefix("dir::")).resolve()
    return (ROOT / value).resolve()


def check_config(config_path: Path, failures: list[str]) -> None:
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        failures.append(f"{config_path.relative_to(ROOT)}: invalid JSON: {exc}")
        return

    missing_keys = sorted(REQUIRED_KEYS - set(config))
    if missing_keys:
        failures.append(f"{config_path.relative_to(ROOT)}: missing keys: {', '.join(missing_keys)}")

    if config.get("DESIGN_NAME") != "hello_chip_top":
        failures.append(f"{config_path.relative_to(ROOT)}: DESIGN_NAME must be hello_chip_top")
    if config.get("CLOCK_PORT") != "CLK_IN":
        failures.append(f"{config_path.relative_to(ROOT)}: CLOCK_PORT must be CLK_IN")
    if not isinstance(config.get("CLOCK_PERIOD"), (int, float)) or config["CLOCK_PERIOD"] <= 0:
        failures.append(f"{config_path.relative_to(ROOT)}: CLOCK_PERIOD must be positive")

    verilog_files = config.get("VERILOG_FILES")
    if not isinstance(verilog_files, list) or not verilog_files:
        failures.append(f"{config_path.relative_to(ROOT)}: VERILOG_FILES must be a non-empty list")
        return
    for entry in verilog_files:
        if not isinstance(entry, str):
            failures.append(f"{config_path.relative_to(ROOT)}: VERILOG_FILES entries must be strings")
            continue
        path = resolve_dir_path(config_path, entry)
        if not path.is_file():
            failures.append(f"{config_path.relative_to(ROOT)}: missing RTL source {entry}")

    for key in ("SIGNOFF_SDC_FILE", "FP_PIN_ORDER_CFG"):
        if key in config:
            value = config[key]
            if not isinstance(value, str):
                failures.append(f"{config_path.relative_to(ROOT)}: {key} must be a string")
                continue
            path = resolve_dir_path(config_path, value)
            if not path.is_file():
                failures.append(f"{config_path.relative_to(ROOT)}: missing {key} file {value}")


def main() -> int:
    failures: list[str] = []
    for config_path in CONFIGS:
        if not config_path.is_file():
            failures.append(f"missing OpenLane config: {config_path.relative_to(ROOT)}")
            continue
        check_config(config_path, failures)

    for path in [
        ROOT / "pd/openroad/hello_soc.tcl",
        ROOT / "pd/constraints/hello_soc.sdc",
        ROOT / "pd/constraints/hello_soc_gf180.sdc",
        ROOT / "pd/pin_order.cfg",
    ]:
        if not path.is_file():
            failures.append(f"missing PD input: {path.relative_to(ROOT)}")

    if failures:
        print("PD preflight check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("PD preflight check passed.")
    if shutil.which("openlane") or shutil.which("flow.tcl"):
        print("PD tool status: OpenLane command found on PATH.")
    elif shutil.which("docker"):
        result = subprocess.run(
            ["docker", "image", "inspect", OPENLANE_IMAGE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            print(f"PD tool status: Docker image installed: {OPENLANE_IMAGE}")
            print(f"PD image digest pin: {OPENLANE_IMAGE_DIGEST}")
        else:
            print(f"PD tool status: Docker is available, but OpenLane image is missing: {OPENLANE_IMAGE}")
            print(
                "PD next command: "
                f"OPENLANE_IMAGE={OPENLANE_IMAGE} "
                f"OPENLANE_IMAGE_DIGEST={OPENLANE_IMAGE_DIGEST} "
                "scripts/install_openlane_image.sh"
            )
    else:
        print("PD tool status: OpenLane command and docker are missing.")
        print("PD next command: install OpenLane 2, or install Docker and rerun pd-preflight-check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
