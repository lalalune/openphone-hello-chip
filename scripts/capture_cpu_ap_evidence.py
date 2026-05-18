#!/usr/bin/env python3
"""Intake real CPU/AP transcripts and print generated-artifact hashes.

This helper does not run Chipyard, OpenSBI, or Linux. It only validates and
archives transcripts produced by an external generated RV64GC AP run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
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
    "ap-benchmarks": ("ap_benchmark_log", "openphone_hello_ap_benchmarks"),
    "isa-cache-mmu": ("isa_cache_mmu_log", "openphone_hello_isa_cache_mmu"),
    "opensbi-boot": ("opensbi_boot_log", "openphone_hello_opensbi_boot"),
    "linux-boot": ("linux_boot_log", "openphone_hello_linux_boot"),
    "trap-timer-irq": ("trap_timer_irq_log", "openphone_hello_trap_timer_irq"),
}

MODE_ENV = {
    "ap-benchmarks": "OPENPHONE_AP_BENCHMARKS_CMD",
    "isa-cache-mmu": "OPENPHONE_ISA_CACHE_MMU_CMD",
    "opensbi-boot": "OPENPHONE_OPENSBI_BOOT_CMD",
    "linux-boot": "OPENPHONE_LINUX_BOOT_CMD",
    "trap-timer-irq": "OPENPHONE_TRAP_TIMER_IRQ_CMD",
}

DTS_BOOT_REQUIREMENTS = {
    "cpu node": [r"\bcpus\s*\{", r"device_type\s*=\s*\"cpu\""],
    "memory node": [r"memory@[0-9a-fA-F]+", r"device_type\s*=\s*\"memory\""],
    "timer node": [r"riscv,clint0", r"riscv,aclint-mtimer", r"riscv,aclint-mswi"],
    "interrupt controller": [r"interrupt-controller", r"riscv,plic0"],
    "uart console": [r"serial@[0-9a-fA-F]+", r"ns16550", r"sifive,uart"],
    "chosen stdout": [r"stdout-path", r"bootargs\s*=.*console="],
    "hello npu mmio": [r"openphone,hello-npu"],
    "hello dma mmio": [r"openphone,hello-dma"],
    "hello display mmio": [r"openphone,hello-display"],
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


def strip_dts_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//.*", "", text)


def dts_audit(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        print(f"STATUS: BLOCKED cpu_ap.dts_boot_audit - DTS is missing: {rel(path)}")
        return 1 if args.require_bootable else 0

    text = path.read_text(encoding="utf-8", errors="ignore")
    uncommented = strip_dts_comments(text)
    missing: list[str] = []
    for label, patterns in DTS_BOOT_REQUIREMENTS.items():
        if not any(re.search(pattern, uncommented, flags=re.I | re.S) for pattern in patterns):
            missing.append(label)
    serial_blocks = re.findall(
        r"serial@[0-9a-fA-F]+\s*\{.*?\n\s*\};", uncommented, flags=re.I | re.S
    )
    if serial_blocks and not any(
        "status" not in block or "disabled" not in block for block in serial_blocks
    ):
        missing.append("enabled uart console")

    dtc_rc = 0
    dtc_msg = "dtc not available"
    if args.run_dtc and shutil.which("dtc"):
        with tempfile.NamedTemporaryFile(suffix=".dtb") as tmp:
            proc = subprocess.run(
                ["dtc", "-I", "dts", "-O", "dtb", "-o", tmp.name, str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            dtc_rc = proc.returncode
            dtc_msg = (proc.stderr or proc.stdout).strip() or "dtc compiled DTS"

    if dtc_rc != 0:
        print(f"STATUS: FAIL cpu_ap.dts_boot_audit - dtc failed for {rel(path)}")
        print(dtc_msg)
        return 1

    if missing:
        print(f"STATUS: BLOCKED cpu_ap.dts_boot_audit - {rel(path)} is not a complete AP boot DTB")
        for item in missing:
            print(f"  - missing {item}")
        if args.run_dtc:
            print(f"  dtc: {dtc_msg}")
        return 1 if args.require_bootable else 0

    print(f"STATUS: PASS cpu_ap.dts_boot_audit - {rel(path)} has AP boot DTB markers")
    if args.run_dtc:
        print(f"  dtc: {dtc_msg}")
    return 0


def intake(args: argparse.Namespace) -> int:
    manifest = load_manifest_or_exit()
    transcript_key, artifact_name = MODE_TO_TRANSCRIPT[args.mode]
    spec = transcript_specs(manifest)[transcript_key]
    generated_manifest = Path(args.generated_manifest)
    if not generated_manifest.is_absolute():
        generated_manifest = ROOT / generated_manifest
    if not generated_manifest.is_file():
        print(
            f"error: generated import manifest does not exist: {rel(generated_manifest)}",
            file=sys.stderr,
        )
        print(
            "STATUS: BLOCKED cpu_ap.transcript_intake - generate/import OpenPhoneRocketConfig before archiving boot evidence"
        )
        return 2
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

    generated_manifest_rel = (
        rel(generated_manifest.resolve())
        if generated_manifest.is_absolute()
        else str(generated_manifest)
    )
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


def template(args: argparse.Namespace) -> int:
    manifest = load_manifest_or_exit()
    modes = [args.mode] if args.mode != "all" else sorted(MODE_TO_TRANSCRIPT)
    for mode in modes:
        transcript_key, artifact_name = MODE_TO_TRANSCRIPT[mode]
        spec = transcript_specs(manifest)[transcript_key]
        print(f"# {mode}: {spec['artifact']}")
        print(f"# destination: {spec['path']}")
        print(f"# command env: {MODE_ENV[mode]}")
        print("# Raw transcript from the generated AP simulator must contain these markers:")
        for marker in spec.get("raw_required_strings", []):
            print(f"# - {marker}")
        print("#")
        print(f"openphone-evidence: template_for={artifact_name}")
        print("openphone-evidence: replace_this_file_with_real_generated_ap_output=true")
        print()
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

    template_parser = sub.add_parser(
        "template",
        help="print required marker checklists for raw generated-AP transcripts",
    )
    template_parser.add_argument("mode", choices=["all", *sorted(MODE_TO_TRANSCRIPT)])
    template_parser.set_defaults(func=template)

    dts_parser = sub.add_parser(
        "dts-audit",
        help="check whether a DTS has the CPU/memory/timer/IRQ/UART markers needed for AP boot",
    )
    dts_parser.add_argument(
        "--path",
        default=str(
            (ROOT / "build/chipyard/openphone_rocket/openphone-hello.dts").relative_to(ROOT)
        ),
        help="DTS path to audit; defaults to the generated selected AP DTS",
    )
    dts_parser.add_argument(
        "--run-dtc",
        action="store_true",
        help="Also compile the DTS with dtc when dtc is available in PATH",
    )
    dts_parser.add_argument(
        "--require-bootable",
        action="store_true",
        help="Return nonzero when AP boot markers are missing",
    )
    dts_parser.set_defaults(func=dts_audit)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
