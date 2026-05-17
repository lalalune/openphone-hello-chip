#!/usr/bin/env sh
set -eu

if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
    echo "qemu-system-riscv64 missing."
    exit 1
fi

if [ ! -f sw/bootrom/hello_qemu_stub.elf ]; then
    echo "sw/bootrom/hello_qemu_stub.elf missing. Install a RISC-V ELF toolchain and build the stub first."
    exit 1
fi

echo "Launching QEMU virt machine as the software reference target. Ctrl-A X exits."
qemu-system-riscv64 -machine virt -nographic -bios none -kernel sw/bootrom/hello_qemu_stub.elf
