# Renode qemu-virt reference target

The Renode platform in this directory mirrors the qemu-virt software reference tier closely enough for early firmware bring-up. It provides an RV64 CPU, RAM at `0x8000_0000`, and a UART at `0x1000_0000`.

This is not the hello-chip hardware ABI. The hello-chip ABI is the CPU-less debug/MMIO contract in `sw/platform/hello_platform_contract.json`; the overlapping `0x1000_0000` qemu-virt UART address must not be treated as the hello peripheral-control block in software that targets real hardware.
