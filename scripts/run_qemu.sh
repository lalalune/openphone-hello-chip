#!/usr/bin/env sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
src="$repo_dir/sw/bootrom/hello_qemu_stub.S"
linker="$repo_dir/sw/bootrom/linker.ld"
checked_elf="$repo_dir/build/qemu/hello_qemu_stub.elf"
legacy_elf="$repo_dir/sw/bootrom/hello_qemu_stub.elf"
banner="openphone hello qemu"
load_addr="0x80000000"
uart_addr="0x10000000"

usage() {
    cat <<EOF
usage: scripts/run_qemu.sh [--check|--build-stub|--elf PATH]

  --check       run semantic checks, build if possible, then bounded QEMU smoke
  --build-stub  build build/qemu/hello_qemu_stub.elf with a local RISC-V toolchain
  --elf PATH    launch an explicit ELF instead of the default stub path
EOF
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

    return 1
}

semantic_check() {
    failed=0

    for path in "$src" "$linker" "$repo_dir/sim/qemu/README.md"; do
        if [ ! -f "$path" ]; then
            echo "missing required qemu-virt artifact: ${path#$repo_dir/}"
            failed=1
        fi
    done

    if [ "$failed" -ne 0 ]; then
        return 1
    fi

    grep -q "$banner" "$src" || {
        echo "sw/bootrom/hello_qemu_stub.S must print '$banner'"
        failed=1
    }
    grep -Eqi "li[[:space:]]+a1,[[:space:]]*$uart_addr" "$src" || {
        echo "sw/bootrom/hello_qemu_stub.S must write the qemu-virt UART at $uart_addr"
        failed=1
    }
    grep -q "$load_addr" "$linker" || {
        echo "sw/bootrom/linker.ld must link the qemu-virt stub at $load_addr"
        failed=1
    }
    grep -q "ENTRY(_start)" "$linker" || {
        echo "sw/bootrom/linker.ld must keep _start as the ELF entry"
        failed=1
    }
    grep -q "software reference only" "$repo_dir/sim/qemu/README.md" || {
        echo "sim/qemu/README.md must mark qemu-virt as software reference only"
        failed=1
    }
    grep -q "scripts/run_qemu.sh --build-stub" "$repo_dir/sim/qemu/README.md" || {
        echo "sim/qemu/README.md must document the stub ELF build path"
        failed=1
    }

    return "$failed"
}

build_stub() {
    cc=$(find_toolchain) || {
        echo "BLOCKED: no RISC-V ELF toolchain found on PATH."
        echo "Install riscv64-unknown-elf-gcc or set RISCV_CC to a compatible compiler."
        return 2
    }

    mkdir -p "$repo_dir/build/qemu"
    "$cc" -nostdlib -nostartfiles -ffreestanding \
        -march=rv64imac -mabi=lp64 \
        -Wl,-T,"$linker" -Wl,--build-id=none \
        -o "$checked_elf" "$src"
    echo "Built ${checked_elf#$repo_dir/} with $cc"
}

run_bounded_smoke() {
    elf=$1

    if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
        echo "BLOCKED: qemu-system-riscv64 missing."
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
        echo "qemu-virt bounded smoke passed: saw '$banner'"
        rm -f "$log"
        return 0
    fi

    echo "qemu-virt bounded smoke failed: did not see '$banner'"
    echo "QEMU log: $log"
    return 1
}

mode=run
elf=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check)
            mode=check
            ;;
        --build-stub)
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
semantic_check

case "$mode" in
    build)
        build_stub
        ;;
    check)
        if build_stub; then
            run_bounded_smoke "$checked_elf"
        else
            status=$?
            if [ "$status" -eq 2 ]; then
                echo "qemu-virt semantic checks passed; executable smoke is blocked until the toolchain is installed."
                exit 0
            fi
            exit "$status"
        fi
        ;;
    run)
        if [ -z "$elf" ]; then
            if [ -f "$checked_elf" ]; then
                elf=$checked_elf
            elif [ -f "$legacy_elf" ]; then
                elf=$legacy_elf
            else
                build_stub || exit $?
                elf=$checked_elf
            fi
        fi

        if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
            echo "qemu-system-riscv64 missing."
            exit 1
        fi
        if [ ! -f "$elf" ]; then
            echo "$elf missing."
            exit 1
        fi

        echo "Launching qemu-virt software reference target. This is not the hello-chip hardware ABI. Ctrl-A X exits."
        qemu-system-riscv64 -machine virt -nographic -bios none -no-reboot -kernel "$elf"
        ;;
esac
