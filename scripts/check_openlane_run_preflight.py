#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "pd/signoff/manifest.yaml"
DEFAULT_OPENLANE_IMAGE = "ghcr.io/efabless/openlane2:2.4.0.dev1"
DEFAULT_OPENLANE_DIGEST = "sha256:bcaabac3b114dfb9e739af9f16b53a79ce1b744bcdb3ad4fc476c961581fe5d5"


def docker_image_id(image: str) -> str | None:
    if not shutil.which("docker"):
        return None
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{index .RepoDigests 0}}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def docker_manifest_contains_digest(image: str, digest: str) -> bool | None:
    if not shutil.which("docker"):
        return None
    result = subprocess.run(
        ["docker", "manifest", "inspect", "--verbose", image],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    return digest in result.stdout


def validate_openlane_config(config_path: Path, failures: list[str]) -> None:
    if not config_path.is_file():
        failures.append(f"missing OpenLane config: {config_path.relative_to(ROOT)}")
        return
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        failures.append(f"{config_path.relative_to(ROOT)}: invalid JSON: {exc}")
        return
    for key in ("DESIGN_NAME", "VERILOG_FILES", "CLOCK_PORT", "CLOCK_PERIOD"):
        if key not in config:
            failures.append(f"{config_path.relative_to(ROOT)}: missing {key}")
    if config.get("DESIGN_NAME") != "hello_chip_top":
        failures.append(f"{config_path.relative_to(ROOT)}: DESIGN_NAME must be hello_chip_top")
    if not isinstance(config.get("VERILOG_FILES"), list) or not config["VERILOG_FILES"]:
        failures.append(f"{config_path.relative_to(ROOT)}: VERILOG_FILES must be a non-empty list")


def main() -> int:
    parser = ArgumentParser(description="Check OpenLane/OpenROAD image and run-root readiness.")
    parser.add_argument(
        "--release",
        action="store_true",
        help="require installed pinned image and at least one run directory",
    )
    args = parser.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text())
    runner = manifest.get("runner", {}) if isinstance(manifest, dict) else {}
    image = runner.get("openlane_image", DEFAULT_OPENLANE_IMAGE)
    digest_pin = runner.get("openlane_image_digest", DEFAULT_OPENLANE_DIGEST)
    failures: list[str] = []
    blockers: list[str] = []
    if not isinstance(image, str) or not image:
        failures.append("pd/signoff/manifest.yaml runner.openlane_image must be a non-empty string")
        image = DEFAULT_OPENLANE_IMAGE
    if not isinstance(digest_pin, str) or not digest_pin.startswith("sha256:"):
        failures.append(
            "pd/signoff/manifest.yaml runner.openlane_image_digest must be a sha256 digest"
        )
        digest_pin = DEFAULT_OPENLANE_DIGEST

    for config_name in (
        "pd/openlane/config.json",
        "pd/openlane/config.sky130.json",
        "pd/openlane/config.gf180.json",
    ):
        validate_openlane_config(ROOT / config_name, failures)

    run_roots = manifest.get("run_roots", [])
    if not isinstance(run_roots, list) or not run_roots:
        failures.append("pd/signoff/manifest.yaml must list run_roots")
    else:
        run_dirs = [
            path for run_root in run_roots for path in (ROOT / run_root).glob("*") if path.is_dir()
        ]
        if not run_dirs:
            blockers.append("no OpenLane/OpenROAD run directories exist under configured run_roots")

    if shutil.which("openlane") or shutil.which("flow.tcl"):
        pass
    else:
        manifest_match = docker_manifest_contains_digest(image, digest_pin)
        digest = docker_image_id(image)
        if digest is None:
            blockers.append(f"OpenLane command missing and Docker image is not installed: {image}")
        elif digest_pin not in digest and manifest_match is not True:
            blockers.append(f"OpenLane Docker image digest is not pinned to {digest_pin}: {digest}")
        if manifest_match is False:
            blockers.append(
                f"OpenLane remote manifest does not contain pinned digest {digest_pin}: {image}"
            )

    if failures:
        print("OpenLane run preflight failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    if blockers:
        print("OpenLane run preflight blockers:")
        for blocker in blockers:
            print(f"  - {blocker}")
        if args.release:
            return 1
        print("OpenLane configs are present; run/image evidence is still blocked.")
        return 0

    print("OpenLane run preflight passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
