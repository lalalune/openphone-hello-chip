# QEMU qemu-virt reference target

QEMU is the qemu-virt software reference only tier. It is not the hello-chip hardware ABI.

The hello chip has no CPU and is driven through the package debug nibble bridge into the MMIO contract recorded in `sw/platform/hello_platform_contract.json`. By contrast, `make qemu` launches `qemu-system-riscv64 -machine virt` with RAM at `0x8000_0000` and a qemu-virt UART at `0x1000_0000`.

The checked-in qemu-virt firmware source is `sw/bootrom/hello_qemu_firmware.S`.
Build it with a local bare-metal RISC-V toolchain:

```sh
scripts/run_qemu.sh --build-firmware
```

That writes `build/qemu/hello_qemu_firmware.elf`. `scripts/run_qemu.sh`
launches that ELF by default. The compatibility alias
`scripts/run_qemu.sh --build-stub` is still accepted, but no checked-in ELF is
used as boot evidence.

`make qemu-check` runs semantic checks for the qemu-virt source, linker script,
and documentation. If `riscv64-unknown-elf-gcc`, `riscv64-elf-gcc`,
`riscv64-linux-gnu-gcc`, or `RISCV_CC` is available, it also builds the firmware
and runs a bounded QEMU smoke that expects the UART banner:

```text
openphone hello qemu
```

On a passing executable smoke, the captured serial transcript is archived at
`build/reports/qemu_smoke.log`. A QEMU status report may be treated as executed
software-reference evidence only when both `STATUS: PASS qemu.check` and that
banner-bearing transcript are present.

Each stage prints an actionable `STATUS: PASS`, `STATUS: BLOCKED`, or
`STATUS: FAIL` line. If the RISC-V toolchain or QEMU is missing, the executable
smoke is explicitly reported as blocked after the semantic checks pass.
`make qemu-check` is the non-strict local status target used by `make smoke`.
`make qemu-check-strict` runs with `REQUIRE_QEMU=1`, so blocked executable smoke
returns nonzero. The project Docker image installs Ubuntu's
`gcc-riscv64-unknown-elf` package so strict QEMU can build a real RISC-V ELF
instead of relying on a checked-in binary.

The next software milestones should add:

```text
timer test
DMA/NPU/display MMIO smoke tests using the central contract
```
