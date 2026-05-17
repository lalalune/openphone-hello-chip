#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)"
firmware="$repo_dir/build/qemu/hello_qemu_firmware.elf"
smoke_log="$repo_dir/build/reports/renode_smoke.log"
smoke_manifest="$repo_dir/build/reports/renode_smoke.manifest"
banner="openphone hello qemu"
transcript=

status_line() {
    state=$1
    check=$2
    detail=$3
    printf 'STATUS: %s %s - %s\n' "$state" "$check" "$detail"
}

usage() {
    cat <<EOF
usage: scripts/run_renode.sh [--check] [--transcript PATH]

  --check            run semantic checks and report executable smoke status
  --transcript PATH  intake a real Renode serial transcript and archive it if it contains the expected banner
EOF
}

mode=run
while [ "$#" -gt 0 ]; do
    case "$1" in
        --check)
            mode=check
            ;;
        --transcript)
            shift
            if [ "$#" -eq 0 ]; then
                usage
                exit 2
            fi
            transcript=$1
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

    for path in "$repl" "$resc" "$readme"; do
        if [ ! -f "$path" ]; then
            status_line "FAIL" "renode.semantic" "missing required scaffold ${path#"$repo_dir"/}"
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

    if [ "$failed" -eq 0 ]; then
        status_line "PASS" "renode.semantic" "platform scaffold and docs match qemu-virt contract"
    fi
    return "$failed"
}

renode_install_hint() {
    cat <<EOF
Renode install/preflight:
  - Install Renode using the official package for this host: https://renode.readthedocs.io/en/latest/introduction/installing.html
  - Confirm the executable is on PATH:
      command -v renode
  - Confirm the CLI starts and reports a version:
      renode --version
  - Run the qemu-virt Renode reference and capture a real serial log:
      scripts/run_renode.sh
  - Archive the captured log as evidence:
      scripts/run_renode.sh --check --transcript path/to/real-renode-serial.log
EOF
}

renode_version() {
    if ! command -v renode >/dev/null 2>&1; then
        return 1
    fi
    renode --version 2>/dev/null | head -n 1 || true
}

renode_version_label() {
    version=$(renode_version || true)
    if [ -n "$version" ]; then
        printf '%s\n' "$version"
    else
        printf 'version-unavailable\n'
    fi
}

renode_missing_detail() {
    # shellcheck disable=SC2016
    printf 'Renode executable missing: command -v renode failed; version unavailable because renode --version could not run; unblock with: install Renode, then run `command -v renode`, `renode --version`, `scripts/run_renode.sh`, and `scripts/run_renode.sh --check --transcript path/to/real-renode-serial.log`.'
}

sha256_file() {
    path=$1
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$path" | awk '{print $1}'
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$path" | awk '{print $1}'
        return 0
    fi
    printf 'unavailable\n'
}

archive_transcript() {
    path=$1

    if [ ! -f "$path" ]; then
        status_line "FAIL" "renode.transcript" "transcript does not exist: $path"
        return 1
    fi
    if [ ! -s "$path" ]; then
        status_line "FAIL" "renode.transcript" "transcript is empty: $path"
        return 1
    fi
    if ! grep -q "$banner" "$path"; then
        status_line "FAIL" "renode.transcript" "transcript did not contain '$banner'"
        return 1
    fi

    mkdir -p "$repo_dir/build/reports"
    cp "$path" "$smoke_log"
    {
        printf 'status=PASS\n'
        printf 'check=renode.run\n'
        printf 'source=%s\n' "$path"
        printf 'archive=%s\n' "${smoke_log#"$repo_dir"/}"
        printf 'sha256=%s\n' "$(sha256_file "$smoke_log")"
        printf 'banner=%s\n' "$banner"
        if command -v renode >/dev/null 2>&1; then
            printf 'renode=%s\n' "$(command -v renode)"
            printf 'renode_version=%s\n' "$(renode_version_label)"
        else
            printf 'renode=missing-on-intake-host\n'
            printf 'renode_version=unavailable-missing-executable\n'
        fi
    } >"$smoke_manifest"
    status_line "PASS" "renode.transcript" "archived transcript with required banner to ${smoke_log#"$repo_dir"/}"
    status_line "PASS" "renode.run" "transcript contains '$banner'; manifest ${smoke_manifest#"$repo_dir"/}"
    return 0
}

blocked() {
    detail=$1
    echo "BLOCKED: $detail"
    status_line "BLOCKED" "renode.run" "$detail"
    if [ "$mode" = "check" ] && [ "${REQUIRE_RENODE:-0}" != "1" ]; then
        status_line "BLOCKED" "renode.check" "semantic checks passed; executable Renode smoke has no transcript"
        exit 0
    fi
    exit 2
}

cd "$repo_dir"
semantic_check || exit 1

if [ -n "$transcript" ]; then
    archive_transcript "$transcript" || exit 1
    if [ "$mode" = "check" ]; then
        status_line "PASS" "renode.check" "semantic checks and transcript intake passed"
        exit 0
    fi
    exit 0
fi

if ! command -v renode >/dev/null 2>&1; then
    renode_install_hint
    blocked "$(renode_missing_detail)"
fi

if [ "$mode" = "check" ]; then
    status_line "PASS" "renode.preflight" "found $(command -v renode) $(renode_version_label)"
    if [ ! -f "$firmware" ]; then
        blocked "Renode executable smoke needs ${firmware#"$repo_dir"/}; run scripts/run_qemu.sh --build-firmware first."
    fi
    blocked "Renode is installed and ${firmware#"$repo_dir"/} exists, but no real transcript was provided. Re-run with --transcript PATH after capturing a Renode serial log containing '$banner'."
fi

echo "Launching Renode qemu-virt software reference target. This is not the hello-chip hardware ABI."
echo "This interactive target does not create release evidence by itself. Capture serial output and run: scripts/run_renode.sh --check --transcript PATH"
renode sim/renode/openphone_hello.resc
