#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)"
firmware="$repo_dir/build/qemu/hello_qemu_firmware.elf"
smoke_log="$repo_dir/build/reports/renode_smoke.log"
smoke_manifest="$repo_dir/build/reports/renode_smoke.manifest"
attempt_log="$repo_dir/build/reports/renode_smoke_attempt.log"
banner_contract="$repo_dir/sim/renode/expected_serial_banner.txt"
banner="openphone hello qemu"
transcript=
smoke_seconds="${RENODE_SMOKE_SECONDS:-5}"

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
  --transcript PATH  intake a Renode serial transcript after validating transcript and local preflight evidence

Environment:
  RENODE_SMOKE_SECONDS  bounded run duration in seconds (default: 5)
EOF
}

expected_banner() {
    if [ -f "$banner_contract" ]; then
        sed -n '1p' "$banner_contract"
    else
        printf '%s\n' "$banner"
    fi
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

    for path in "$repl" "$resc" "$readme" "$banner_contract"; do
        if [ ! -f "$path" ]; then
            status_line "FAIL" "renode.semantic" "missing required scaffold ${path#"$repo_dir"/}"
            failed=1
        fi
    done

    if [ "$failed" -ne 0 ]; then
        return 1
    fi

    if [ "$(expected_banner)" != "$banner" ]; then
        status_line "FAIL" "renode.semantic" "sim/renode/expected_serial_banner.txt must contain exactly '$banner'"
        failed=1
    fi

    grep -q "0x80000000" "$repl" || {
        status_line "FAIL" "renode.semantic" "Renode RAM must cover qemu-virt load address 0x80000000"
        failed=1
    }
    grep -q "0x10000000" "$repl" || {
        status_line "FAIL" "renode.semantic" "Renode UART must match qemu-virt UART 0x10000000"
        failed=1
    }
    grep -q "LoadELF @build/qemu/hello_qemu_firmware.elf" "$resc" || {
        status_line "FAIL" "renode.semantic" "sim/renode/openphone_hello.resc must load the qemu-virt firmware ELF"
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
        status_line "PASS" "renode.semantic" "platform scaffold, docs, and serial banner contract match qemu-virt"
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
  - Build or provide the qemu-virt reference firmware:
      scripts/run_qemu.sh --build-firmware
  - Run the bounded qemu-virt Renode reference check:
      make renode-check
  - If you capture serial manually, archive it as evidence:
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
    printf 'Renode executable missing: command -v renode failed; version unavailable because renode --version could not run; unblock with: install Renode, then run `command -v renode`, `renode --version`, `scripts/run_qemu.sh --build-firmware`, and `make renode-check`.'
}

require_renode_preflight() {
    if ! command -v renode >/dev/null 2>&1; then
        renode_install_hint
        echo "BLOCKED: $(renode_missing_detail)"
        status_line "BLOCKED" "renode.transcript" "cannot intake transcript without a local renode executable and version preflight"
        return 2
    fi

    version=$(renode_version || true)
    if [ -z "$version" ]; then
        status_line "BLOCKED" "renode.transcript" "renode exists at $(command -v renode), but renode --version produced no usable version"
        return 2
    fi

    if [ ! -f "$firmware" ]; then
        status_line "BLOCKED" "renode.transcript" "cannot intake transcript without ${firmware#"$repo_dir"/}; run scripts/run_qemu.sh --build-firmware first"
        return 2
    fi

    return 0
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

validate_transcript_file() {
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

    return 0
}

manifest_value() {
    key=$1
    file=$2
    awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; found=1; exit } END { if (!found) exit 1 }' "$file"
}

validate_manifest() {
    manifest=$1
    transcript_hash=$2
    firmware_hash=$3

    for key in status check evidence_kind archive sha256 banner banner_contract firmware firmware_sha256 renode renode_version; do
        if ! manifest_value "$key" "$manifest" >/dev/null 2>&1; then
            status_line "FAIL" "renode.manifest" "manifest missing required field: $key"
            return 1
        fi
    done

    if [ "$(manifest_value status "$manifest")" != "PASS" ]; then
        status_line "FAIL" "renode.manifest" "manifest status is not PASS"
        return 1
    fi
    if [ "$(manifest_value check "$manifest")" != "renode.run" ]; then
        status_line "FAIL" "renode.manifest" "manifest check is not renode.run"
        return 1
    fi
    if [ "$(manifest_value evidence_kind "$manifest")" != "renode-executable-transcript" ]; then
        status_line "FAIL" "renode.manifest" "manifest evidence_kind does not mark executable transcript evidence"
        return 1
    fi
    if [ "$(manifest_value sha256 "$manifest")" != "$transcript_hash" ]; then
        status_line "FAIL" "renode.manifest" "manifest transcript hash does not match archived log"
        return 1
    fi
    if [ "$(manifest_value firmware_sha256 "$manifest")" != "$firmware_hash" ]; then
        status_line "FAIL" "renode.manifest" "manifest firmware hash does not match preflight firmware"
        return 1
    fi
    if [ "$(manifest_value banner "$manifest")" != "$banner" ]; then
        status_line "FAIL" "renode.manifest" "manifest banner does not match required serial banner"
        return 1
    fi
    if [ "$(manifest_value banner_contract "$manifest")" != "${banner_contract#"$repo_dir"/}" ]; then
        status_line "FAIL" "renode.manifest" "manifest banner_contract does not match required serial banner contract"
        return 1
    fi

    return 0
}

archive_transcript() {
    path=$1

    validate_transcript_file "$path" || return $?
    require_renode_preflight || return $?

    mkdir -p "$repo_dir/build/reports"
    cp "$path" "$smoke_log"
    transcript_hash=$(sha256_file "$smoke_log")
    firmware_hash=$(sha256_file "$firmware")
    {
        printf 'status=PASS\n'
        printf 'check=renode.run\n'
        printf 'evidence_kind=renode-executable-transcript\n'
        printf 'source=%s\n' "$path"
        printf 'archive=%s\n' "${smoke_log#"$repo_dir"/}"
        printf 'sha256=%s\n' "$transcript_hash"
        printf 'banner=%s\n' "$banner"
        printf 'banner_contract=%s\n' "${banner_contract#"$repo_dir"/}"
        printf 'firmware=%s\n' "${firmware#"$repo_dir"/}"
        printf 'firmware_sha256=%s\n' "$firmware_hash"
        printf 'renode=%s\n' "$(command -v renode)"
        printf 'renode_version=%s\n' "$(renode_version_label)"
    } >"$smoke_manifest"
    validate_manifest "$smoke_manifest" "$transcript_hash" "$firmware_hash" || return 1
    status_line "PASS" "renode.transcript" "archived transcript with required banner to ${smoke_log#"$repo_dir"/}"
    status_line "PASS" "renode.manifest" "validated executable transcript manifest ${smoke_manifest#"$repo_dir"/}"
    status_line "PASS" "renode.run" "transcript contains '$banner'; manifest ${smoke_manifest#"$repo_dir"/}"
    return 0
}

write_run_manifest() {
    source_log=$1
    state=$2
    detail=$3
    transcript_hash=$(sha256_file "$source_log")
    firmware_hash=$(sha256_file "$firmware")

    {
        printf 'status=%s\n' "$state"
        printf 'check=renode.run\n'
        printf 'evidence_kind=renode-executable-transcript\n'
        printf 'source=%s\n' "${source_log#"$repo_dir"/}"
        printf 'archive=%s\n' "${smoke_log#"$repo_dir"/}"
        printf 'sha256=%s\n' "$transcript_hash"
        printf 'banner=%s\n' "$banner"
        printf 'banner_contract=%s\n' "${banner_contract#"$repo_dir"/}"
        printf 'firmware=%s\n' "${firmware#"$repo_dir"/}"
        printf 'firmware_sha256=%s\n' "$firmware_hash"
        printf 'renode=%s\n' "$(command -v renode)"
        printf 'renode_version=%s\n' "$(renode_version_label)"
        printf 'renode_command=renode --console --disable-xwt sim/renode/openphone_hello.resc\n'
        printf 'duration_seconds=%s\n' "$smoke_seconds"
        printf 'detail=%s\n' "$detail"
    } >"$smoke_manifest"
}

run_bounded_smoke() {
    mkdir -p "$repo_dir/build/reports"
    rm -f "$attempt_log"

    renode --console --disable-xwt sim/renode/openphone_hello.resc >"$attempt_log" 2>&1 &
    renode_pid=$!

    sleep "$smoke_seconds"
    if kill -0 "$renode_pid" >/dev/null 2>&1; then
        kill "$renode_pid" >/dev/null 2>&1 || true
    fi
    wait "$renode_pid" >/dev/null 2>&1 || true

    if grep -q "$banner" "$attempt_log"; then
        cp "$attempt_log" "$smoke_log"
        write_run_manifest "$smoke_log" "PASS" "bounded Renode stdout/stderr contained expected serial banner"
        validate_manifest "$smoke_manifest" "$(sha256_file "$smoke_log")" "$(sha256_file "$firmware")" || return 1
        status_line "PASS" "renode.manifest" "validated executable transcript manifest ${smoke_manifest#"$repo_dir"/}"
        status_line "PASS" "renode.run" "bounded smoke saw '$banner'; archived ${smoke_log#"$repo_dir"/}"
        return 0
    fi

    write_run_manifest "$attempt_log" "FAIL" "bounded Renode stdout/stderr did not contain expected serial banner"
    status_line "FAIL" "renode.run" "bounded smoke did not see '$banner'; attempt log ${attempt_log#"$repo_dir"/}"
    return 1
}

blocked() {
    detail=$1
    echo "BLOCKED: $detail"
    status_line "BLOCKED" "renode.run" "$detail"
    if [ "$mode" = "check" ] && [ "${REQUIRE_RENODE:-0}" != "1" ]; then
        status_line "BLOCKED" "renode.check" "semantic checks passed; $detail"
        exit 0
    fi
    exit 2
}

cd "$repo_dir"
semantic_check || exit 1

if [ -n "$transcript" ]; then
    archive_transcript "$transcript" || exit $?
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
    status_line "PASS" "renode.preflight" "firmware present ${firmware#"$repo_dir"/}; attempting bounded Renode run for ${smoke_seconds}s"
    if run_bounded_smoke; then
        status_line "PASS" "renode.check" "semantic, preflight, and executable smoke passed"
        exit 0
    fi
    exit 1
fi

echo "Launching Renode qemu-virt software reference target. This is not the hello-chip hardware ABI."
echo "This interactive target does not create release evidence by itself. For bounded evidence run: make renode-check"
if [ ! -f "$firmware" ]; then
    blocked "Renode run needs ${firmware#"$repo_dir"/}; run scripts/run_qemu.sh --build-firmware first."
fi
renode sim/renode/openphone_hello.resc
