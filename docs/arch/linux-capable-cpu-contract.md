# Linux-capable CPU/AP contract

This document is a requirements gate, not implementation evidence. The current
repo-local executable CPU path is the tiny contract model in
`rtl/cpu/hello_cpu_subsystem_stub.sv`; it is useful for fetch/execute and bus
bring-up, but it is not a Linux-capable hart.

It also separates two targets that must not be conflated:

- `OpenPhoneRocketConfig` is the first generated RV64GC Linux bring-up path.
- A 2028 phone-class application processor is blocked until separate AP
  topology, ISA, cache/MMU, benchmark, power/thermal, Android, and silicon
  evidence exists.

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

The selected single Rocket path is not a phone-class AP target. It can close a
Linux boot smoke gate, firmware handoff gate, and driver bring-up gate. It
cannot close any 2028 phone-class claim without a new selected CPU subsystem
plan and the evidence below.

## 2028 Phone-Class AP Claim Requirements

Before documentation, manifests, or release reports may describe the project as
a 2028 phone-class application processor, the CPU/AP workstream must provide:

| Area | Required evidence |
| --- | --- |
| CPU topology | Application-hart count, microarchitecture choice, frequency/voltage targets, DVFS states, management/security core split, and rationale against contemporary phone AP workloads. |
| ISA compliance | RISC-V application profile or explicit equivalent, extension matrix, `misa`/`riscv_hwprobe` evidence, ISA compliance logs, atomics, compressed instructions, counters, and userspace ABI proof. |
| Cache and coherency | cache hierarchy evidence covering I-cache, D-cache, shared-cache or LLC policy, line size, maintenance operations, DMA/NPU coherency contract, stress tests, and MPKI/counter evidence. |
| MMU | Supported virtual-memory modes such as Sv39 or stronger, TLB behavior, page-table walk behavior, shootdown path, fault precision, and Linux `CONFIG_MMU` boot evidence. |
| Boot | Reset ROM, OpenSBI, U-Boot or documented bootloader equivalent, generated DTS hash, Linux initramfs, Android userspace plan, and serial transcripts from the selected AP target. |
| Benchmarks | CoreMark/MHz, STREAM, `lmbench` bandwidth/latency, `fio`, selected SPEC-like kernels, run count, clocks, memory config, thermal state, power method, and raw artifacts. |
| Android and product | CTS/VTS/userspace evidence, scheduler/thermal integration, security/debug lifecycle, and phone-board evidence before compatibility or product claims. |

Until all of those gates pass, the allowed claim is only "generated Rocket
RV64GC Linux bring-up path selected, evidence blocked."

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
| `build/evidence/cpu_ap/openphone_hello_isa_cache_mmu.log` | ISA profile, `misa`, `riscv_hwprobe`, required base extension visibility, Sv39 or stronger MMU evidence, I-cache/D-cache/L2 cache parameters, cache-line size, TLB behavior, and page-table evidence. |
| `build/evidence/cpu_ap/openphone_hello_ap_benchmarks.log` | Benchmark report SHA-256, claim level, CoreMark/MHz, STREAM Triad, `lat_mem_rd`, `fio`, CPU frequency, run count, thermal state, and power method. |

## Exact Linux-Capable Gate States

`docs/evidence/cpu-ap-evidence-manifest.json` is the source of truth for the
current gate states. Every gate below is intentionally `blocked` until its
evidence path exists, is bound to
`build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`, and the
archived transcript ends with `openphone-evidence: status=PASS`.

| Gate | Evidence required before PASS |
| --- | --- |
| `rv64gc_isa` | RV64GC ISA profile, `misa`, `Zicsr`, `Zifencei`, and `riscv_hwprobe` markers. |
| `s_mode_privilege` | M-mode and S-mode CSR/delegation markers including `mstatus`, `medeleg`, `mideleg`, `satp`, and `sret`. |
| `mmu_sv39_or_stronger` | Sv39 or stronger MMU evidence, `satp`, TLB behavior, page-table evidence, and Linux `CONFIG_MMU`. |
| `clint_timer_software_irq` | CLINT/ACLINT `mtime`, `mtimecmp`, `msip`, timer interrupt, and software interrupt evidence. |
| `plic_external_irq` | PLIC-compatible interrupt-controller node plus external interrupt claim/complete evidence. |
| `uart_console` | UART console path visible to firmware and Linux early console. |
| `dtb_linux_boot_contract` | Generated DTS with CPU, memory, timer, interrupt-controller, UART, and chosen stdout nodes. |
| `opensbi_handoff` | OpenSBI transcript reaching the next-stage handoff on the selected memory map. |
| `linux_initramfs_smoke` | Linux early console, initramfs start, and hello MMIO smoke result from the generated AP target. |

QEMU `virt` OS boot attempts are useful software-reference evidence only. The
bounded attempt log at `build/reports/qemu_os_boot_attempt.log` may be
`BLOCKED`, `FAIL`, or `PASS`, but it cannot satisfy any generated
Chipyard/Rocket AP gate.

The current tiny CPU cannot produce these markers because it has no CSR file,
trap vector, privilege mode, timer facility, OpenSBI handoff, Linux early
console, or firmware-to-kernel handoff path.

## Actionable Next Commands

Run the local non-claiming scaffold checks:

```sh
make chipyard-generator-check cpu-ap-scaffold-check cpu-ap-completion-gate
```

Prepare the external generated AP path:

```sh
python3 scripts/check_chipyard_import_preflight.py --require-checkout
make chipyard-generated-check
```

Archive real transcripts only after the generated AP target has produced them:

```sh
python3 scripts/capture_cpu_ap_evidence.py intake opensbi-boot --source /path/to/opensbi.log --command '/exact/boot command'
python3 scripts/capture_cpu_ap_evidence.py intake linux-boot --source /path/to/linux.log --command '/exact/boot command'
python3 scripts/capture_cpu_ap_evidence.py intake trap-timer-irq --source /path/to/trap.log --command '/exact/test command'
python3 scripts/capture_cpu_ap_evidence.py intake isa-cache-mmu --source /path/to/isa-cache-mmu.log --command '/exact/isa-cache-mmu command'
python3 scripts/capture_cpu_ap_evidence.py intake ap-benchmarks --source /path/to/ap-benchmarks.log --command '/exact/benchmark command'
python3 scripts/capture_cpu_ap_evidence.py hashes
```
