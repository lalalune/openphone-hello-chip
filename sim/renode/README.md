# Renode qemu-virt reference target

Renode is a qemu-virt software reference only tier. The checked-in reference by
itself is not boot evidence for the qemu-virt path and is not the hello-chip
hardware ABI. In short, this is not the hello-chip hardware ABI.

The platform in this directory mirrors enough of the qemu-virt reference shape
for early firmware bring-up experiments: an RV64 CPU, RAM at `0x8000_0000`, and
a UART at `0x1000_0000`. The hello-chip ABI remains the CPU-less debug/MMIO
contract in `sw/platform/hello_platform_contract.json`; the overlapping
`0x1000_0000` qemu-virt UART address must not be treated as the hello
peripheral-control block in software that targets real hardware.

`scripts/run_renode.sh --check` is fail-closed. It checks that the platform and
documentation match the qemu-virt contract, then reports executable smoke as
`STATUS: BLOCKED` unless a real Renode serial transcript path exists. A future
passing smoke must load `build/qemu/hello_qemu_firmware.elf` and capture the
UART banner:

```text
openphone hello qemu
```

Until that transcript is automated and checked in, Renode status may be
described only as reference-only or blocked, not booted.
