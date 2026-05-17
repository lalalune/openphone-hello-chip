# QEMU qemu-virt reference target

QEMU is the qemu-virt software reference only tier. It is not the hello-chip hardware ABI.

The hello chip has no CPU and is driven through the package debug nibble bridge into the MMIO contract recorded in `sw/platform/hello_platform_contract.json`. By contrast, `make qemu` launches `qemu-system-riscv64 -machine virt` with RAM at `0x8000_0000` and a qemu-virt UART at `0x1000_0000`.

The checked-in qemu-virt firmware source is `sw/bootrom/hello_qemu_stub.S`.
Build it with a local bare-metal RISC-V toolchain:

```sh
scripts/run_qemu.sh --build-stub
```

That writes `build/qemu/hello_qemu_stub.elf`. `scripts/run_qemu.sh` launches
that ELF by default, falling back to the legacy checked-in path
`sw/bootrom/hello_qemu_stub.elf` only if it already exists.

`make qemu-check` runs semantic checks for the qemu-virt source, linker script,
and documentation. If `riscv64-unknown-elf-gcc`, `riscv64-elf-gcc`,
`riscv64-linux-gnu-gcc`, or `RISCV_CC` is available, it also builds the stub and
runs a bounded QEMU smoke that expects the UART banner:

```text
openphone hello qemu
```

If the RISC-V toolchain is missing, the executable smoke is explicitly blocked
after the semantic checks pass.

The next software milestones should add:

```text
timer test
DMA/NPU/display MMIO smoke tests using the central contract
```
