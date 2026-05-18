# CPU/AP Evidence Capture

This directory documents CPU/AP evidence expectations. Linux-capable AP evidence
for the generated Chipyard `OpenPhoneRocketConfig` target is archived under
`build/evidence/cpu_ap/`, not committed here.

QEMU `virt` boot logs are software-reference evidence only. They do not satisfy
the generated AP OpenSBI/Linux/trap/cache/benchmark gates.

Required generated-target evidence paths:

- `build/evidence/cpu_ap/openphone_hello_opensbi_boot.log`
- `build/evidence/cpu_ap/openphone_hello_linux_boot.log`
- `build/evidence/cpu_ap/openphone_hello_trap_timer_irq.log`
- `build/evidence/cpu_ap/openphone_hello_isa_cache_mmu.log`
- `build/evidence/cpu_ap/openphone_hello_ap_benchmarks.log`

Use these commands to see the marker checklist, archive real generated-AP logs,
and check the result:

```sh
python3 scripts/capture_cpu_ap_evidence.py template all
scripts/capture_chipyard_linux_evidence.sh --help
python3 scripts/check_cpu_ap_evidence.py --require-evidence
python3 scripts/check_chipyard_generated_linux_contract.py --require-boot-evidence
```

The capture wrapper requires one command environment variable per transcript.
Each command must run the generated AP simulator or generated-target test and
print the real transcript to stdout/stderr. The wrapper keeps raw output in
`build/evidence/cpu_ap/raw/` and only writes accepted evidence after the intake
validator sees the required markers and binds the transcript to
`build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`.

## Pass criteria

A generated AP evidence set must show all of the following across the accepted
logs:

1. OpenSBI reset, CSR, timer, interrupt-controller, UART, DRAM, and next-stage
   handoff markers.
2. Linux early console, generated DTS hash, DT boot nodes, `CONFIG_MMU`,
   initramfs start, and hello MMIO smoke result markers.
3. Trap, timer, software IRQ, PLIC external IRQ claim/complete, `mret`, and
   `sret` markers.
4. RV64GC, `misa`, `riscv_hwprobe`, `Zicsr`, `Zifencei`, Sv39, cache, TLB, and
   page-table markers.
5. Benchmark report hash, CoreMark/MHz, STREAM Triad, `lat_mem_rd`, `fio`, CPU
   frequency, run count, thermal state, and power method markers.

## Linux Host Flow

On the Linux host, first generate/build the pinned Chipyard target and create
`build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`. Then set
the command variables consumed by `scripts/capture_chipyard_linux_evidence.sh`.

The two boot captures may use the same simulator command if one full boot log
contains all OpenSBI and Linux markers. Trap/cache/benchmark captures should
point at generated-target tests or scripts that emit those specific results.
Do not edit raw transcripts to make the intake pass; fix the simulator payload
or test command and rerun the capture.

After all captures pass, copy the printed `artifact_sha256.*` and
`evidence_sha256.*` values from `python3 scripts/capture_cpu_ap_evidence.py
hashes` into the generated import manifest, then rerun the checks above.
