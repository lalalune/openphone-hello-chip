# Renode Tier-2 Linux boot on the openagent-e1 CPU variant

This recipe proves that **our platform contract**
(`sw/platform/e1_platform_contract.json`, section `e1_chip_cpu_variant`)
is sufficient to boot a real Linux + busybox userspace under Renode — no RTL
or FPGA required.

## What this branch produced

| Path                                                  | Purpose |
|-------------------------------------------------------|---------|
| `sim/renode/openagent_e1.repl`                     | Renode platform model — UART @ 0x10001000, PLIC @ 0x0C000000, CLINT @ 0x02000000, DRAM @ 0x80000000 (256 MiB), DMA/NPU/display stubs at the contract addresses. |
| `sim/renode/openagent_e1_tier2.resc`               | Boot script: loads `fw_payload.elf` (OpenSBI + kernel) and starts the machine, attaching the analyzer to `uart0`. |
| `sim/renode/openagent_e1_tier2.robot`              | Robot test — waits for `openagent tier2: linux booted` and the `/ #` busybox prompt within 60 s. |
| `scripts/sim/run_renode_tier2.sh`                     | Wrapper: runs `renode-test` and tees to `build/sim/renode/tier2.log`. |
| `sw/opensbi/platform/openagent/{platform.c,objects.mk,config.mk,README.md}` | OpenSBI platform glue for our addresses — to be copied into the OpenSBI source tree before building. |

## Reproducing end-to-end

Inputs from the `ws/boot-tier2-linux-busybox` worktree:

- `external/linux/arch/riscv/boot/Image` — riscv64 kernel (rv64gc), with
  the init script printing `openagent tier2: linux booted` before spawning
  busybox sh.
- `build/initramfs/openagent_tier2.cpio.gz` — busybox rootfs.

Build OpenSBI for our platform (host: any RISC-V GCC, e.g.
`riscv64-unknown-elf-gcc`):

```sh
cp -r sw/opensbi/platform/openagent external/opensbi/platform/
make -C external/opensbi PLATFORM=openagent \
    FW_PAYLOAD_PATH=$(pwd)/external/linux/arch/riscv/boot/Image
```

Run the smoke:

```sh
./scripts/sim/run_renode_tier2.sh
```

Expected console (in `build/sim/renode/tier2.log`):

```
OpenSBI v...
Platform Name             : openagent-e1-cpu-variant
Platform Features         : ...
Platform HART Count       : 1
Boot HART ID              : 0
Firmware Base             : 0x80000000
...
[    0.000000] Linux version ...
[    0.xxxxxx] Console: ttyS0 at MMIO 0x10001000 (irq = 1)
openagent tier2: linux booted
/ #
```

## Current status on this worktree

Renode CLI is installed (`/opt/homebrew/bin/renode`,
`/opt/homebrew/bin/renode-test`). The `.repl` / `.resc` / `.robot` files and
the OpenSBI platform sources are committed. The build inputs
(`fw_payload.elf`, kernel `Image`, initramfs `.cpio.gz`) are produced on the
sibling `ws/boot-tier2-linux-busybox` branch and were **not present in this
worktree at scaffold time**, so an end-to-end run has not been executed
here. Re-run `./scripts/sim/run_renode_tier2.sh` after merging
`ws/boot-tier2-linux-busybox` and building OpenSBI as above.

## Why these addresses

All addresses come from
`sw/platform/e1_platform_contract.json :: e1_chip_cpu_variant`. The
contract is the single source of truth shared by RTL decode, the kernel
DTS, U-Boot, OpenSBI, and the AOSP HAL. This Renode model deliberately
does **not** use QEMU virt addresses (UART at 0x10000000) — it uses our
0x10001000 — so a successful boot on this model is positive evidence that
our contract is internally consistent and Linux-bootable.
