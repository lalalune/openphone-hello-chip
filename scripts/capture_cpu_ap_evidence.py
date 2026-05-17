#!/usr/bin/env python3
"""Intake real CPU/AP transcripts and print generated-artifact hashes.

This helper does not run Chipyard, OpenSBI, or Linux. It only validates and
archives transcripts produced by an external generated RV64GC AP run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from cpu_ap_evidence_lib import (
    GENERATED_MANIFEST,
    ROOT,
    artifact_specs,
    load_evidence_manifest,
    rel,
    sha256_path,
    text_problems,
    transcript_specs,
)

MODE_TO_TRANSCRIPT = {
    "opensbi-boot": ("opensbi_boot_log", "openphone_hello_opensbi_boot"),
    "linux-boot": ("linux_boot_log", "openphone_hello_linux_boot"),
    "trap-timer-irq": ("trap_timer_irq_log", "openphone_hello_trap_timer_irq"),
}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_manifest_or_exit() -> dict:
    errors: list[str] = []
    manifest = load_evidence_manifest(errors)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
    return manifest


def intake(args: argparse.Namespace) -> int:
    manifest = load_manifest_or_exit()
    transcript_key, artifact_name = MODE_TO_TRANSCRIPT[args.mode]
    spec = transcript_specs(manifest)[transcript_key]
    source = Path(args.source).expanduser()
    if not source.is_file():
        print(f"error: source transcript does not exist: {source}", file=sys.stderr)
        return 1

    raw_text = source.read_text(encoding="utf-8", errors="ignore")
    problems = text_problems(str(args.command) + "\n" + raw_text, spec, str(source), raw=True)
    if problems:
        print("STATUS: FAIL cpu_ap.transcript_intake - source transcript is not acceptable")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    generated_manifest = Path(args.generated_manifest)
    if not generated_manifest.is_absolute():
        generated_manifest = ROOT / generated_manifest
    generated_manifest_rel = (
        rel(generated_manifest.resolve())
        if generated_manifest.is_absolute()
        else str(generated_manifest)
    )
    generated_manifest_sha = "missing"
    if generated_manifest.is_file():
        generated_manifest_sha = sha256_path(generated_manifest)

    destination = ROOT / str(spec["path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    captured = "\n".join(
        [
            f"openphone-evidence: target=cpu_ap artifact={artifact_name}",
            f"openphone-evidence: source={source}",
            f"openphone-evidence: command={args.command}",
            f"openphone-evidence: generated_manifest={generated_manifest_rel}",
            f"openphone-evidence: generated_manifest_sha256={generated_manifest_sha}",
            f"openphone-evidence: intake_utc={utc_now()}",
            "openphone-evidence: raw_transcript_begin",
            raw_text.rstrip(),
            "openphone-evidence: raw_transcript_end",
            "openphone-evidence: status=PASS",
            "",
        ]
    )
    destination.write_text(captured, encoding="utf-8")
    digest = sha256_path(destination)
    print(f"STATUS: PASS cpu_ap.transcript_intake - archived {rel(destination)} sha256={digest}")
    print(f"  update generated import manifest evidence_sha256.{spec['sha256_key']}={digest}")
    return 0


def hashes(_: argparse.Namespace) -> int:
    manifest = load_manifest_or_exit()
    print("CPU/AP generated artifact hashes for import manifest:")
    for name, spec in artifact_specs(manifest).items():
        path = ROOT / str(spec["path"])
        if path.exists():
            print(f"  artifact_sha256.{spec['sha256_key']}={sha256_path(path)}  # {name}")
        else:
            print(f"  missing {spec['path']}  # {name}")
    print("CPU/AP transcript hashes for import manifest:")
    for name, spec in transcript_specs(manifest).items():
        path = ROOT / str(spec["path"])
        if path.exists():
            print(f"  evidence_sha256.{spec['sha256_key']}={sha256_path(path)}  # {name}")
        else:
            print(f"  missing {spec['path']}  # {name}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    intake_parser = sub.add_parser("intake", help="validate and archive a real transcript")
    intake_parser.add_argument("mode", choices=sorted(MODE_TO_TRANSCRIPT))
    intake_parser.add_argument(
        "--source", required=True, help="Path to the captured external transcript"
    )
    intake_parser.add_argument(
        "--command",
        required=True,
        help="Exact command that produced the transcript; this is recorded as evidence metadata",
    )
    intake_parser.add_argument(
        "--generated-manifest",
        default=str(GENERATED_MANIFEST.relative_to(ROOT)),
        help="Generated import manifest used for this run",
    )
    intake_parser.set_defaults(func=intake)

    hashes_parser = sub.add_parser("hashes", help="print hashes for existing CPU/AP artifacts")
    hashes_parser.set_defaults(func=hashes)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
