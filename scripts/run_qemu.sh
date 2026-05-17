#!/usr/bin/env sh
set -eu

if ! command -v qemu-system-riscv64 >/dev/null 2>&1; then
    echo "qemu-system-riscv64 missing."
    exit 1
fi

if [ ! -f sw/bootrom/hello_qemu_stub.elf ]; then
    echo "sw/bootrom/hello_qemu_stub.elf missing."
    echo "This target is qemu-virt software reference only; build the qemu-virt stub first with a RISC-V ELF toolchain."
    exit 1
fi

echo "Launching qemu-virt software reference target. This is not the hello-chip hardware ABI. Ctrl-A X exits."
qemu-system-riscv64 -machine virt -nographic -bios none -kernel sw/bootrom/hello_qemu_stub.elf
