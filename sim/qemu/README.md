# QEMU qemu-virt reference target

QEMU is the qemu-virt software reference only tier. It is not the hello-chip hardware ABI.

The hello chip has no CPU and is driven through the package debug nibble bridge into the MMIO contract recorded in `sw/platform/hello_platform_contract.json`. By contrast, `make qemu` launches `qemu-system-riscv64 -machine virt` with RAM at `0x8000_0000` and a qemu-virt UART at `0x1000_0000`.

The current repository does not yet include a RISC-V cross-compiled firmware ELF, so `make qemu` checks for `sw/bootrom/hello_qemu_stub.elf` before launching.

The first real software milestone should add:

```text
riscv64-unknown-elf toolchain setup
boot ROM/startup assembly
UART printf
timer test
DMA/NPU/display MMIO smoke tests using the central contract
```
