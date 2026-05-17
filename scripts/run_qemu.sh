#!/usr/bin/env sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
src="$repo_dir/sw/bootrom/hello_qemu_firmware.S"
linker="$repo_dir/sw/bootrom/linker.ld"
checked_elf="$repo_dir/build/qemu/hello_qemu_firmware.elf"
smoke_log="$repo_dir/build/reports/qemu_smoke.log"
banner="openphone hello qemu"
load_addr="0x80000000"
uart_addr="0x10000000"

usage() {
    cat <<EOF
usage: scripts/run_qemu.sh [--check|--build-firmware|--build-stub|--elf PATH]

  --check           run semantic checks, build if possible, then bounded QEMU smoke
  --build-firmware  build build/qemu/hello_qemu_firmware.elf with a local RISC-V toolchain
  --build-stub      compatibility alias for --build-firmware
  --elf PATH        launch an explicit ELF instead of the default firmware path
EOF
}

status_line() {
    state=$1
    check=$2
    detail=$3
    printf 'STATUS: %s %s - %s\n' "$state" "$check" "$detail"
}

find_toolchain() {
    if [ -n "${RISCV_CC:-}" ]; then
        command -v "$RISCV_CC" >/dev/null 2>&1 && {
            printf '%s\n' "$RISCV_CC"
            return 0
        }
        return 1
    fi

    for cc in riscv64-unknown-elf-gcc riscv64-elf-gcc riscv64-linux-gnu-gcc; do
        if command -v "$cc" >/dev/null 2>&1; then
            printf '%s\n' "$cc"
            return 0
        fi
    done

    for cc in /opt/homebrew/opt/llvm/bin/clang clang; do
        if command -v "$cc" >/dev/null 2>&1; then
            if "$cc" --target=riscv64-unknown-elf -fuse-ld=lld -x assembler -c /dev/null -o /tmp/openphone-riscv-toolchain-test.o >/dev/null 2>&1; then
                rm -f /tmp/openphone-riscv-toolchain-test.o
                printf '%s\n' "$cc"
                return 0
            fi
            rm -f /tmp/openphone-riscv-toolchain-test.o
        fi
    done

    return 1
}

explain_toolchain_blocker() {
    cat <<EOF
BLOCKED: no RISC-V ELF toolchain found on PATH.
Install one of:
  - Ubuntu/Debian: apt-get install gcc-riscv64-unknown-elf
  - Other systems: riscv64-unknown-elf-gcc or riscv64-elf-gcc
  - macOS/Homebrew LLVM: /opt/homebrew/opt/llvm/bin/clang with lld
Or set RISCV_CC to a compatible compiler.
EOF
}

semantic_check() {
    failed=0

    for path in "$src" "$linker" "$repo_dir/sim/qemu/README.md"; do
        if [ ! -f "$path" ]; then
            status_line "FAIL" "qemu.semantic" "missing required artifact ${path#$repo_dir/}"
            failed=1
        fi
    done

    if [ "$failed" -ne 0 ]; then
        return 1
    fi

    grep -q "$banner" "$src" || {
        status_line "FAIL" "qemu.semantic" "sw/bootrom/hello_qemu_firmware.S must print '$banner'"
        failed=1
    }
    grep -q "HELLO_QEMU_VIRT_UART_BASE" "$src" || grep -Eqi "li[[:space:]]+a1,[[:space:]]*$uart_addr" "$src" || {
        status_line "FAIL" "qemu.semantic" "firmware must write the qemu-virt UART at $uart_addr via the platform contract"
        failed=1
    }
    grep -q "$load_addr" "$linker" || {
        status_line "FAIL" "qemu.semantic" "sw/bootrom/linker.ld must link qemu-virt firmware at $load_addr"
        failed=1
    }
    grep -q "ENTRY(_start)" "$linker" || {
        status_line "FAIL" "qemu.semantic" "sw/bootrom/linker.ld must keep _start as the ELF entry"
        failed=1
    }
    grep -q "software reference only" "$repo_dir/sim/qemu/README.md" || {
        status_line "FAIL" "qemu.semantic" "sim/qemu/README.md must mark qemu-virt as software reference only"
        failed=1
    }
    grep -q "scripts/run_qemu.sh --build-firmware" "$repo_dir/sim/qemu/README.md" || {
        status_line "FAIL" "qemu.semantic" "sim/qemu/README.md must document the firmware ELF build path"
        failed=1
    }

    if [ "$failed" -eq 0 ]; then
        status_line "PASS" "qemu.semantic" "source, linker, and docs match qemu-virt contract"
    fi
    return "$failed"
}

build_firmware() {
    cc=$(find_toolchain) || {
        explain_toolchain_blocker
        status_line "BLOCKED" "qemu.build" "install a RISC-V ELF compiler or set RISCV_CC"
        return 2
    }

    mkdir -p "$repo_dir/build/qemu"
    if [ "$(basename "$cc")" = "clang" ]; then
        set -- "$cc" --target=riscv64-unknown-elf -fuse-ld=lld
    else
        set -- "$cc"
    fi

    if ! "$@" -nostdlib -nostartfiles -ffreestanding \
        -march=rv64imac -mabi=lp64 \
        -Wl,-T,"$linker" -Wl,--build-id=none \
        -o "$checked_elf" "$src"; then
        status_line "FAIL" "qemu.build" "$cc could not build ${src#$repo_dir/}"
        return 1
    fi
    status_line "PASS" "qemu.build" "built ${checked_elf#$repo_dir/} with $cc"
}

run_bounded_smoke() {
    elf=$1

    if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
        echo "BLOCKED: qemu-system-riscv64 missing."
        status_line "BLOCKED" "qemu.run" "install qemu-system-riscv64 for executable serial smoke"
        return 2
    fi

    log=$(mktemp "${TMPDIR:-/tmp}/hello-qemu.XXXXXX")
    qemu-system-riscv64 -machine virt -nographic -bios none -no-reboot -kernel "$elf" >"$log" 2>&1 &
    qemu_pid=$!

    sleep "${QEMU_SMOKE_SECONDS:-2}"
    if kill -0 "$qemu_pid" >/dev/null 2>&1; then
        kill "$qemu_pid" >/dev/null 2>&1 || true
    fi
    wait "$qemu_pid" >/dev/null 2>&1 || true

    if grep -q "$banner" "$log"; then
        mkdir -p "$repo_dir/build/reports"
        cp "$log" "$smoke_log"
        status_line "PASS" "qemu.run" "bounded smoke saw '$banner'; archived ${smoke_log#$repo_dir/}"
        rm -f "$log"
        return 0
    fi

    mkdir -p "$repo_dir/build/reports"
    cp "$log" "$smoke_log"
    status_line "FAIL" "qemu.run" "bounded smoke did not see '$banner'"
    echo "QEMU log: $smoke_log"
    rm -f "$log"
    return 1
}

mode=run
elf=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check)
            mode=check
            ;;
        --build-firmware|--build-stub)
            mode=build
            ;;
        --elf)
            shift
            if [ "$#" -eq 0 ]; then
                usage
                exit 2
            fi
            elf=$1
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

cd "$repo_dir"
if ! semantic_check; then
    exit 1
fi

case "$mode" in
    build)
        build_firmware
        ;;
    check)
        if build_firmware; then
            if run_bounded_smoke "$checked_elf"; then
                status_line "PASS" "qemu.check" "semantic, build, and executable smoke passed"
            else
                status=$?
                if [ "$status" -eq 2 ]; then
                    status_line "BLOCKED" "qemu.check" "semantic/build passed; executable smoke needs qemu-system-riscv64"
                    if [ "${REQUIRE_QEMU:-0}" != "1" ]; then
                        exit 0
                    fi
                fi
                exit "$status"
            fi
        else
            status=$?
            if [ "$status" -eq 2 ]; then
                status_line "BLOCKED" "qemu.check" "semantic checks passed; executable smoke needs a RISC-V ELF toolchain"
                if [ "${REQUIRE_QEMU:-0}" != "1" ]; then
                    exit 0
                fi
            fi
            exit "$status"
        fi
        ;;
    run)
        if [ -z "$elf" ]; then
            if [ -f "$checked_elf" ]; then
                elf=$checked_elf
            else
                build_firmware || exit $?
                elf=$checked_elf
            fi
        fi

        if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
            echo "BLOCKED: qemu-system-riscv64 missing."
            status_line "BLOCKED" "qemu.run" "install qemu-system-riscv64 or run scripts/run_qemu.sh --check for non-strict status"
            exit 2
        fi
        if [ ! -f "$elf" ]; then
            status_line "FAIL" "qemu.run" "$elf missing"
            exit 1
        fi

        echo "Launching qemu-virt software reference target. This is not the hello-chip hardware ABI. Ctrl-A X exits."
        qemu-system-riscv64 -machine virt -nographic -bios none -no-reboot -kernel "$elf"
        ;;
esac
