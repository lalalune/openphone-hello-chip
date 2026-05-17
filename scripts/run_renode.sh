#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
firmware="$repo_dir/build/qemu/hello_qemu_firmware.elf"
banner="openphone hello qemu"

status_line() {
    state=$1
    check=$2
    detail=$3
    printf 'STATUS: %s %s - %s\n' "$state" "$check" "$detail"
}

usage() {
    cat <<EOF
usage: scripts/run_renode.sh [--check]

  --check  run semantic checks and report executable smoke as blocked until proven
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
    readme="$repo_dir/sim/renode/README.md"

    for path in "$repl" "$resc" "$readme"; do
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
        status_line "FAIL" "renode.semantic" "sim/renode/README.md must mark Renode as software reference only"
        failed=1
    }
    grep -q "hello-chip hardware ABI" "$readme" || {
        status_line "FAIL" "renode.semantic" "sim/renode/README.md must separate Renode from hello-chip hardware ABI"
        failed=1
    }
    grep -q "$banner" "$readme" || {
        status_line "FAIL" "renode.semantic" "sim/renode/README.md must name the serial banner required for future smoke evidence"
        failed=1
    }

    if [ "$failed" -eq 0 ]; then
        status_line "PASS" "renode.semantic" "platform scaffold and docs match qemu-virt contract"
    fi
    return "$failed"
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

if ! command -v renode >/dev/null 2>&1; then
    blocked "Renode missing. qemu-virt scaffold is present, but no Renode boot transcript was produced."
fi

if [ "$mode" = "check" ]; then
    if [ ! -f "$firmware" ]; then
        blocked "Renode executable smoke needs ${firmware#$repo_dir/}; run scripts/run_qemu.sh --build-firmware first."
    fi
    blocked "Renode is installed and ${firmware#$repo_dir/} exists, but this repo does not yet have an automated Renode serial transcript check for '$banner'."
fi

echo "Launching Renode qemu-virt software reference target. This is not the hello-chip hardware ABI."
renode sim/renode/openphone_hello.resc
