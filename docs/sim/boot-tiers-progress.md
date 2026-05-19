# Boot Tiers 0 & 1 — QEMU virt bring-up progress

Branch: `ws/boot-tier0-1`

## Status (2026-05-18)

| Tier | Artifact | Built? | Booted? |
|------|----------|--------|---------|
| 0    | `fw/bare-metal/hello/hello.elf` — bare-metal "HELLO\n" via 16550 UART @ 0x10000000 | NO — blocked on RV64 toolchain | NO |
| 1    | OpenSBI generic `fw_payload.elf` wrapping `fw/opensbi-payloads/hello-smode/hello.bin` | NO — blocked on RV64 toolchain | NO |

`qemu-system-riscv64` is installed (Homebrew, at `/opt/homebrew/bin/qemu-system-riscv64`).
`gtimeout` is installed. The blocker is a RISC-V cross-compiler — neither
`riscv64-unknown-elf-gcc` nor `riscv64-linux-gnu-gcc` is on PATH. A separate agent
(`ws/toolchain-riscv64`) is provisioning the toolchain.

## Files scaffolded on this branch

```
fw/bare-metal/hello/{reset.S, hello.c, linker.ld, Makefile}
fw/opensbi-payloads/hello-smode/{reset.S, hello.c, linker.ld, Makefile}
scripts/sim/run_qemu_baremetal.sh        # tier 0 boot + log + assert HELLO
scripts/build/build_opensbi_qemu.sh      # clones opensbi v1.4, builds fw_payload
scripts/sim/run_qemu_opensbi.sh          # tier 1 boot + assert banner + payload string
docs/sim/boot-tiers-progress.md          # this file
```

## Design notes

- **UART address.** Tier 0 and Tier 1 target the **QEMU virt** UART at
  `0x10000000` (16550A) so they validate on a stock machine. Our project
  platform contract (`sw/platform/hello_platform_contract.json`) places the
  UART at `0x10001000`; later tiers will use a custom machine or DTS overlay
  to relocate to that address. This is intentional and documented in the C
  source headers.
- **Link addresses.** Tier 0 ELF at `0x80000000` (QEMU `-kernel` default for
  RV64 virt). Tier 1 payload at `0x80200000` (OpenSBI generic S-mode jump
  target — `FW_TEXT_START` 0x80000000 + 2 MiB).
- **Reset.S** parks secondary harts on `wfi`, sets sp on hart 0, calls
  `main()`. After `uart_puts(...)`, `main()` enters a `wfi` loop.
- **Compiler flags.** `-nostdlib -nostartfiles -ffreestanding -mcmodel=medany
  -march=rv64imac -mabi=lp64 -O2`.
- **No SBI console use in Tier 1.** The S-mode payload pokes the 16550
  directly so the test does not depend on SBI extensions being negotiated.
  OpenSBI's PMP defaults allow S-mode UART access on virt.

## Exact reproduction once the toolchain lands

Assuming `riscv64-unknown-elf-gcc` is on PATH (otherwise pass
`CROSS=riscv64-linux-gnu-` / `CROSS_COMPILE=riscv64-linux-gnu-`):

```bash
# --- Tier 0 ---
make -C fw/bare-metal/hello
scripts/sim/run_qemu_baremetal.sh
# Expected: build/sim/qemu/tier0_baremetal.log contains "HELLO"

# --- Tier 1 ---
make -C fw/opensbi-payloads/hello-smode
scripts/build/build_opensbi_qemu.sh
scripts/sim/run_qemu_opensbi.sh
# Expected: build/sim/qemu/tier1_opensbi.log contains the OpenSBI banner
# and "HELLO from S-mode"
```

## Manual one-liners (no helper scripts)

```bash
# Tier 0
qemu-system-riscv64 -machine virt -nographic -bios none \
  -kernel fw/bare-metal/hello/hello.elf \
  -monitor none -serial mon:stdio -no-reboot

# Tier 1
qemu-system-riscv64 -machine virt -nographic \
  -bios external/opensbi/build/platform/generic/firmware/fw_payload.elf \
  -monitor none -serial mon:stdio -no-reboot
```

Exit QEMU with `Ctrl-A x`.

## Verification attempted on this branch

```
$ which riscv64-unknown-elf-gcc riscv64-linux-gnu-gcc
riscv64-unknown-elf-gcc not found
riscv64-linux-gnu-gcc not found
$ which qemu-system-riscv64 gtimeout
/opt/homebrew/bin/qemu-system-riscv64
/opt/homebrew/bin/gtimeout
```

`make -C fw/bare-metal/hello` was not attempted because no cross compiler
is available; the Makefile would fail with `command not found`.
