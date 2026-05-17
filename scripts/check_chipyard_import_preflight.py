#!/usr/bin/env python3
"""Validate the pinned Chipyard checkout before any Rocket import/generation claim."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generators/chipyard/openphone-rocket-manifest.json"
DEFAULT_CHECKOUT = ROOT / "external/chipyard"
DEFAULT_REPORT = ROOT / "build/chipyard/openphone_rocket/bootstrap-preflight.json"


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkout", default=str(DEFAULT_CHECKOUT), help="Path to a Chipyard checkout"
    )
    parser.add_argument(
        "--write-report", default=str(DEFAULT_REPORT), help="Write JSON preflight report"
    )
    parser.add_argument(
        "--require-checkout", action="store_true", help="Return non-zero if checkout is absent"
    )
    parser.add_argument(
        "--skip-remote", action="store_true", help="Skip git ls-remote tag validation"
    )
    args = parser.parse_args()

    manifest = load_manifest()
    chipyard = manifest["chipyard"]
    selected = manifest["selected_path"]
    checkout = Path(args.checkout)
    report_path = Path(args.write_report)
    if not report_path.is_absolute():
        report_path = ROOT / report_path

    errors: list[str] = []
    blockers: list[str] = []
    checks: dict[str, object] = {}
    evidence: dict[str, object] = {
        "schema": "openphone.cpu_ap_bootstrap_preflight.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "checkout": str(checkout),
        "chipyard": {
            "repo": chipyard.get("repo"),
            "tag": chipyard.get("tag"),
            "commit": chipyard.get("commit"),
        },
        "selected_path": {
            "config_name": selected.get("config_name"),
            "core": selected.get("core"),
            "isa": selected.get("isa"),
            "harts": selected.get("harts"),
        },
        "checks": checks,
    }

    if shutil.which("git") is None:
        errors.append("git is not available")
    else:
        checks["git_available"] = True

    if not args.skip_remote and not errors:
        remote = run(
            ["git", "ls-remote", "--tags", chipyard["repo"], f"refs/tags/{chipyard['tag']}"]
        )
        checks["remote_tag_output"] = remote.stdout.strip()
        if remote.returncode != 0:
            errors.append("could not query pinned Chipyard tag from remote")
        else:
            resolved = remote.stdout.split()[0] if remote.stdout.split() else ""
            if resolved != chipyard["commit"]:
                errors.append(
                    f"remote tag {chipyard['tag']} resolves to {resolved}, expected {chipyard['commit']}"
                )

    if not checkout.is_dir():
        blockers.append(f"missing Chipyard checkout: {checkout}")
    elif not (checkout / ".git").exists():
        errors.append(f"checkout is not a git repository: {checkout}")
    elif not errors:
        head = run(["git", "rev-parse", "HEAD"], cwd=checkout)
        checks["checkout_head"] = head.stdout.strip()
        if head.returncode != 0:
            errors.append("could not read Chipyard checkout HEAD")
        elif head.stdout.strip() != chipyard["commit"]:
            errors.append(f"checkout HEAD is {head.stdout.strip()}, expected {chipyard['commit']}")

        submodules = run(["git", "submodule", "status", "--recursive"], cwd=checkout)
        submodule_lines = [line for line in submodules.stdout.splitlines() if line.strip()]
        checks["submodule_count"] = len(submodule_lines)
        if submodules.returncode != 0:
            errors.append("could not read Chipyard recursive submodule status")
        elif not submodule_lines:
            errors.append("Chipyard checkout has no recursive submodule status output")
        elif any(line.startswith("-") or line.startswith("+") for line in submodule_lines):
            errors.append("Chipyard recursive submodules are not initialized at recorded SHAs")

        for relative in ("generators/rocket-chip", "sims/verilator", "software/firemarshal"):
            path = checkout / relative
            checks[f"exists:{relative}"] = path.exists()
            if not path.exists():
                errors.append(f"Chipyard checkout lacks expected path: {relative}")

    evidence["status"] = "fail" if errors else "blocked" if blockers else "pass"
    evidence["errors"] = errors
    evidence["blockers"] = blockers
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("STATUS: FAIL chipyard.import_preflight - pinned checkout validation failed")
        for error in errors:
            print(f"  - {error}")
        print(f"REPORT: {report_path.relative_to(ROOT)}")
        return 1

    if blockers:
        print(
            "STATUS: BLOCKED chipyard.import_preflight - external Chipyard checkout is not available"
        )
        for blocker in blockers:
            print(f"  - {blocker}")
        print(f"REPORT: {report_path.relative_to(ROOT)}")
        return 1 if args.require_checkout else 0

    print(
        "STATUS: PASS chipyard.import_preflight - pinned Chipyard checkout is ready for Rocket import"
    )
    print(f"REPORT: {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
