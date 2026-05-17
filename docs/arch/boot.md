# Boot flow

## Hello chip

The hello chip boot ROM is an identity ROM used by simulation and synthesis checks:

```text
0x0000_0000 = "OPSO"
0x0000_0004 = "CHIP"
0x0000_0008 = contract version 1
0x0000_000C = boot vector placeholder
```

The package-level hello chip still uses the package debug nibble bridge as its board-smoke bus master. The machine-readable software contract is `sw/platform/hello_platform_contract.json`; generated software constants live in `sw/platform/generated/hello_platform_contract.h`.

The CPU subsystem boundary now has a tiny executable RISC-V path for simulation proof. In the focused CPU/contract wrapper, a loader writes a program into the DRAM aperture at `0x8000_0000`, then releases `hello_cpu_subsystem_stub` with `RESET_PC=0x8000_0000`. The CPU fetches from DRAM, executes the minimal integer subset documented in `docs/arch/cpu-subsystem.md`, and halts on `ECALL`.

The identity ROM remains a contract ROM for the package debug path, not a full firmware ROM. A production boot handoff still needs ROM code that sets up M-mode state and jumps to OpenSBI or another firmware payload.

QEMU and Renode do not model this ABI yet. They are qemu-virt software reference targets for early firmware scaffolding, with their own CPU, RAM, and UART contract.

## Full SoC target

```text
reset
management core starts from ROM
clock/reset controller releases application CPU
OpenSBI runs in M-mode
U-Boot loads kernel, initramfs, and device tree
Linux boots with serial console
Android userspace boots on the same hardware contract
```
