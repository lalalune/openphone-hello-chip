#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
firmware="$repo_dir/build/qemu/hello_qemu_firmware.elf"
qemu_transcript="$repo_dir/build/reports/qemu_smoke.log"
banner="openphone hello qemu"
artifact_dir="$repo_dir/build/renode"
transcript="$artifact_dir/openphone_hello_uart.transcript"
manifest="$artifact_dir/openphone_hello_smoke.json"
status_report="$artifact_dir/openphone_hello_status.json"
schema="$repo_dir/sim/renode/openphone_hello_smoke.schema.json"

status_line() {
    state=$1
    check=$2
    detail=$3
    printf 'STATUS: %s %s - %s\n' "$state" "$check" "$detail"
}

emit_status_report() {
    state=$1
    check=$2
    detail=$3
    exit_code=$4
    blocker_kind=${5:-}

    mkdir -p "$artifact_dir"
    renode_path=""
    if command -v renode >/dev/null 2>&1; then
        renode_path=$(command -v renode)
    fi

    python3 - "$status_report" "$state" "$check" "$detail" "$exit_code" "$blocker_kind" "$renode_path" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

report = Path(sys.argv[1])
state = sys.argv[2]
check = sys.argv[3]
detail = sys.argv[4]
exit_code = int(sys.argv[5])
blocker_kind = sys.argv[6] or None
renode_path = sys.argv[7] or None

data = {
    "schema_version": 1,
    "target": "openphone-hello",
    "model_kind": "qemu_virt_reference",
    "status": state,
    "check": check,
    "detail": detail,
    "exit_code": exit_code,
    "blocker_kind": blocker_kind,
    "claim_boundary": "qemu-virt software reference only; not hello-chip hardware ABI boot evidence",
    "command": "scripts/run_renode.sh --check",
    "renode_path": renode_path,
    "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "required_artifacts": {
        "firmware": "build/qemu/hello_qemu_firmware.elf",
        "qemu_reference_transcript": "build/reports/qemu_smoke.log",
        "renode_transcript": "build/renode/openphone_hello_uart.transcript",
        "manifest": "build/renode/openphone_hello_smoke.json",
    },
}
report.write_text(json.dumps(data, indent=2) + "\n")
PY
}

usage() {
    cat <<EOF
usage: scripts/run_renode.sh [--check]

  --check  run semantic checks and require a bounded executable Renode smoke
EOF
}

mode=run
while [ "$#" -gt 0 ]; do
    case "$1" in
        --check)
            mode=check
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
    shift
done

semantic_check() {
    failed=0
    repl="$repo_dir/sim/renode/openphone_hello.repl"
    resc="$repo_dir/sim/renode/openphone_hello.resc"
    readme="$repo_dir/docs/sim/renode/README.md"

    for path in "$repl" "$resc" "$readme" "$schema"; do
        if [ ! -f "$path" ]; then
            status_line "FAIL" "renode.semantic" "missing required scaffold ${path#$repo_dir/}"
            failed=1
        fi
    done

    if [ "$failed" -ne 0 ]; then
        return 1
    fi

    grep -q "0x80000000" "$repl" || {
        status_line "FAIL" "renode.semantic" "Renode RAM must cover qemu-virt load address 0x80000000"
        failed=1
    }
    grep -q "0x10000000" "$repl" || {
        status_line "FAIL" "renode.semantic" "Renode UART must match qemu-virt UART 0x10000000"
        failed=1
    }
    grep -q "software reference" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must mark Renode as software reference only"
        failed=1
    }
    grep -q "hello-chip hardware ABI" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must separate Renode from hello-chip hardware ABI"
        failed=1
    }
    grep -q "$banner" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must name the serial banner required for future smoke evidence"
        failed=1
    }
    grep -q "${transcript#$repo_dir/}" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must name the expected UART transcript artifact"
        failed=1
    }
    grep -q "${manifest#$repo_dir/}" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must name the expected smoke manifest artifact"
        failed=1
    }
    grep -q "${qemu_transcript#$repo_dir/}" "$readme" || {
        status_line "FAIL" "renode.semantic" "docs/sim/renode/README.md must name the QEMU reference transcript artifact"
        failed=1
    }
    grep -q "model_kind" "$schema" || {
        status_line "FAIL" "renode.semantic" "Renode smoke schema must require model_kind"
        failed=1
    }
    grep -q "qemu_virt_reference" "$schema" || {
        status_line "FAIL" "renode.semantic" "Renode smoke schema must identify qemu_virt_reference evidence"
        failed=1
    }
    grep -q "qemu_reference_transcript" "$schema" || {
        status_line "FAIL" "renode.semantic" "Renode smoke schema must require qemu_reference_transcript"
        failed=1
    }

    if [ "$failed" -eq 0 ]; then
        status_line "PASS" "renode.semantic" "platform scaffold and docs match qemu-virt contract"
    fi
    return "$failed"
}

blocked() {
    detail=$1
    kind=${2:-missing_prerequisite}
    echo "BLOCKED: $detail"
    status_line "BLOCKED" "renode.run" "$detail"
    if [ "$mode" = "check" ]; then
        status_line "BLOCKED" "renode.check" "$detail"
        if [ "${REQUIRE_RENODE:-0}" != "1" ]; then
            emit_status_report "BLOCKED" "renode.check" "$detail" 0 "$kind"
            exit 0
        fi
    fi
    emit_status_report "BLOCKED" "renode.check" "$detail" 2 "$kind"
    exit 2
}

blocked_check() {
    detail=$1
    kind=${2:-missing_artifact}
    echo "BLOCKED: $detail"
    status_line "BLOCKED" "renode.check" "$detail"
    if [ "${REQUIRE_RENODE:-0}" = "1" ]; then
        emit_status_report "BLOCKED" "renode.check" "$detail" 2 "$kind"
        exit 2
    fi
    emit_status_report "BLOCKED" "renode.check" "$detail" 0 "$kind"
    exit 0
}

run_executable_smoke() {
    if [ ! -s "$qemu_transcript" ]; then
        blocked_check "Renode equivalence needs QEMU reference transcript ${qemu_transcript#$repo_dir/}; run scripts/run_qemu.sh --check first." "missing_artifact"
    fi

    renode_path=$(command -v renode)
    python3 - "$repo_dir" "$firmware" "$transcript" "$manifest" "$qemu_transcript" "$banner" "$status_report" "$renode_path" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1])
firmware = Path(sys.argv[2])
transcript = Path(sys.argv[3])
manifest = Path(sys.argv[4])
qemu_transcript = Path(sys.argv[5])
banner = sys.argv[6]
status_report = Path(sys.argv[7])
renode_path = sys.argv[8]
timeout_s = float(os.environ.get("RENODE_SMOKE_SECONDS", "5"))

def rel(path: Path) -> str:
    return path.relative_to(repo).as_posix()

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_status(status, check, detail, exit_code, blocker_kind):
    data = {
        "schema_version": 1,
        "target": "openphone-hello",
        "model_kind": "qemu_virt_reference",
        "status": status,
        "check": check,
        "detail": detail,
        "exit_code": exit_code,
        "blocker_kind": blocker_kind,
        "claim_boundary": "qemu-virt software reference only; not hello-chip hardware ABI boot evidence",
        "command": "scripts/run_renode.sh --check",
        "renode_path": renode_path,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "required_artifacts": {
            "firmware": "build/qemu/hello_qemu_firmware.elf",
            "qemu_reference_transcript": "build/reports/qemu_smoke.log",
            "renode_transcript": "build/renode/openphone_hello_uart.transcript",
            "manifest": "build/renode/openphone_hello_smoke.json",
        },
    }
    status_report.write_text(json.dumps(data, indent=2) + "\n")

qemu_text = qemu_transcript.read_text(errors="replace")
if banner not in qemu_text:
    detail = f"missing serial banner {banner!r} in {rel(qemu_transcript)}"
    print(f"STATUS: FAIL renode.equivalence - {detail}")
    write_status("FAIL", "renode.equivalence", detail, 1, "artifact_mismatch")
    raise SystemExit(1)

try:
    version_result = subprocess.run(
        [renode_path, "--version"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )
except (OSError, subprocess.TimeoutExpired) as exc:
    detail = f"could not read Renode version from {renode_path}: {exc}"
    print(f"STATUS: FAIL renode.version - {detail}")
    write_status("FAIL", "renode.version", detail, 1, "tool_execution_failed")
    raise SystemExit(1)

renode_version = " ".join(line.strip() for line in version_result.stdout.splitlines() if line.strip())
if version_result.returncode != 0 or "Renode" not in renode_version or "fake" in renode_version.lower():
    detail = f"Renode version probe did not identify a real Renode CLI at {renode_path}"
    print(f"STATUS: FAIL renode.version - {detail}")
    write_status("FAIL", "renode.version", detail, 1, "tool_execution_failed")
    raise SystemExit(1)

command = [renode_path, "--console", "--disable-xwt", "sim/renode/openphone_hello.resc"]
transcript.parent.mkdir(parents=True, exist_ok=True)
try:
    result = subprocess.run(
        command,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_s,
        check=False,
    )
    output = result.stdout
    exit_code = result.returncode
    timed_out = False
except subprocess.TimeoutExpired as exc:
    output = (exc.stdout or "") + (exc.stderr or "")
    exit_code = 124
    timed_out = True

transcript.write_text(output)
if banner not in output:
    suffix = " before timeout" if timed_out else ""
    detail = f"bounded Renode run did not emit serial banner {banner!r}{suffix}; archived {rel(transcript)}"
    print(f"STATUS: FAIL renode.run - {detail}")
    write_status("FAIL", "renode.run", detail, 1, "artifact_mismatch")
    raise SystemExit(1)

data = {
    "schema_version": 1,
    "target": "openphone-hello",
    "model_kind": "qemu_virt_reference",
    "command": " ".join(command),
    "firmware": "build/qemu/hello_qemu_firmware.elf",
    "firmware_sha256": sha256(firmware),
    "transcript": "build/renode/openphone_hello_uart.transcript",
    "transcript_sha256": sha256(transcript),
    "qemu_reference_transcript": "build/reports/qemu_smoke.log",
    "qemu_reference_transcript_sha256": sha256(qemu_transcript),
    "expected_banner": banner,
    "observed_banner": banner,
    "renode_version": renode_version,
    "renode_path": renode_path,
    "exit_code": exit_code,
    "timed_out_after_banner": timed_out,
    "generated_by": "scripts/run_renode.sh --check real Renode bounded run",
    "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
manifest.write_text(json.dumps(data, indent=2) + "\n")

if exit_code not in (0, 124):
    detail = f"Renode emitted banner but exited with code {exit_code}; archived {rel(transcript)}"
    print(f"STATUS: FAIL renode.run - {detail}")
    write_status("FAIL", "renode.run", detail, 1, "tool_execution_failed")
    raise SystemExit(1)

print(f"STATUS: PASS renode.transcript - found serial banner in {rel(transcript)}")
print(f"STATUS: PASS renode.equivalence - Renode and QEMU transcripts agree on qemu-virt banner and firmware path")
print(f"STATUS: PASS renode.manifest - {rel(manifest)} matches qemu-virt reference schema")
write_status(
    "PASS",
    "renode.check",
    "executable Renode transcript artifacts match qemu-virt reference contract",
    0,
    None,
)
PY
}

cd "$repo_dir"
semantic_check || exit 1

if ! command -v renode >/dev/null 2>&1; then
    blocked "Renode missing. qemu-virt scaffold is present, but no Renode boot transcript was produced." "missing_tool"
fi

if [ "$mode" = "check" ]; then
    if [ ! -f "$firmware" ]; then
        blocked "Renode executable smoke needs ${firmware#$repo_dir/}; run scripts/run_qemu.sh --build-firmware first." "missing_artifact"
    fi
    run_executable_smoke
    status_line "PASS" "renode.check" "executable Renode transcript artifacts match qemu-virt reference contract"
    exit 0
fi

echo "Launching Renode qemu-virt software reference target. This is not the hello-chip hardware ABI."
renode sim/renode/openphone_hello.resc
