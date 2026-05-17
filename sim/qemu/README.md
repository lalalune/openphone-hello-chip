# QEMU reference target

QEMU is the software reference tier. The current repository does not yet include a RISC-V cross-compiled firmware ELF, so `make qemu` checks for `sw/bootrom/hello_qemu_stub.elf` before launching.

The first real software milestone should add:

```text
riscv64-unknown-elf toolchain setup
boot ROM/startup assembly
UART printf
timer test
DMA/NPU/display MMIO smoke tests
```
