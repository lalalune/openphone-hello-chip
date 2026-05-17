# Linux-capable CPU contract

This document is a requirements gate, not implementation evidence. The current
repo-local executable CPU path is the tiny contract model in
`rtl/cpu/hello_cpu_subsystem_stub.sv`; it is useful for fetch/execute and bus
bring-up, but it is not a Linux-capable hart.

## Current Evidence Boundary

| Area | Evidence allowed today |
| --- | --- |
| CPU execution | Tiny RV instruction subset fetches from DRAM through AXI-Lite and halts fail-closed on unsupported instructions or bus errors. |
| Boot | Focused cocotb wrapper preloads DRAM and releases reset at `0x8000_0000`. |
| Interrupts | Timer, software, and external IRQ levels are reflected through `irq_pending`; no trap entry occurs. |
| Memory | AXI-Lite DRAM aperture is sufficient for tiny programs and contract tests only. |
| Linux/AP claims | Blocked. QEMU and Renode remain software-reference targets, not hello-chip hardware proof. |

## Selected AP Path

`generators/chipyard/openphone-rocket-manifest.json` pins the selected generated
AP path:

- Chipyard `1.13.0` at commit
  `69eba860a352343e4ac6b6df0f3638a79a86ec78`.
- Single Rocket RV64GC hart for the first AP integration.
- Project config name `OpenPhoneRocketConfig`.
- Production wrapper name `openphone_rocket_ap`.

The local tiny CPU must not be expanded into a Linux AP. It remains a contract
test scaffold until generated Rocket/Chipyard artifacts and evidence replace or
wrap the boundary.

## Minimum CSR, Trap, And Timer Requirements

A Linux-capable AP path must implement or integrate a core/platform with at
least:

- RV64 privileged M-mode entry with `mstatus`, `misa`, `mie`, `mip`, `mtvec`,
  `mepc`, `mcause`, `mtval`, `mscratch`, `medeleg`, `mideleg`, and `mret`.
- S-mode support required by OpenSBI/Linux, including `satp`, `sstatus`,
  `sie`, `sip`, `stvec`, `sepc`, `scause`, `stval`, and `sret`.
- CLINT-compatible machine timer/software interrupt semantics or a documented
  equivalent consumed by OpenSBI: `mtime`, `mtimecmp`, and `msip`.
- External interrupt target compatible with the selected Linux interrupt
  controller binding, with claim/complete semantics tested from firmware.
- Trap entry that records the precise faulting PC/cause for illegal
  instruction, load/store/fetch access fault, timer interrupt, software
  interrupt, and external interrupt.
- Reset handoff from ROM or firmware entry, with a checked serial transcript
  proving OpenSBI reaches the next boot stage on the hello-chip memory map.

## Required Evidence Artifacts

Placeholder files do not close this gate; each log must come from the selected
generated or wrapped CPU/AP target and must include the listed markers.

| Artifact | Required markers |
| --- | --- |
| `build/evidence/cpu_ap/openphone_hello_opensbi_boot.log` | Reset PC, hart ID, `misa`, `mstatus`, `mtvec`, timer source, interrupt controller, UART console, DRAM base/size, and OpenSBI next-stage handoff. |
| `build/evidence/cpu_ap/openphone_hello_linux_boot.log` | Linux early console, generated DTS hash, memory node, CPU node, timer node, interrupt-controller node, UART node, initramfs start, and hello MMIO smoke result. |
| `build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log` | Illegal-instruction trap with `mcause`, `mepc`, and `mtval`; load/store/fetch access-fault traps; `mtime`/`mtimecmp` timer interrupt; software interrupt through `msip`; external interrupt claim/complete; return path through `mret` or `sret` as appropriate. |

The current tiny CPU cannot produce these markers because it has no CSR file,
trap vector, privilege mode, timer facility, OpenSBI handoff, Linux early
console, or firmware-to-kernel handoff path.
