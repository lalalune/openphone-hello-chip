# Linux CPU/AP Boot Evidence Inventory

Status: local platform contract clear; executable generated-AP Linux boot
evidence still blocked.

This directory tracks Linux boot-facing evidence for the selected CPU/AP path.
It separates locally checkable platform contracts from transcripts that must
come from a real simulator or target run.

## Local Gates

Run these from the repository root:

```sh
python3 scripts/check_linux_platform_contract.py
python3 scripts/check_linux_memory_platform_contract.py
python3 scripts/capture_cpu_ap_evidence.py dts-audit \
  --path sw/linux/dts/openphone-hello.dts \
  --run-dtc \
  --require-hello-peripherals \
  --require-bootable
python3 scripts/check_linux_hardware_contract_gate.py
python3 scripts/check_chipyard_generated_linux_contract.py
```

`check_linux_platform_contract.py` verifies the locally solvable pieces:

- `sw/linux/dts/openphone-hello.dts` exposes RV64GC, Sv39, memory, CLINT, PLIC,
  ns16550 console, and `openphone,hello-*` MMIO nodes.
- `sw/linux/drivers/hello` binds the DTS compatibles and does not advertise
  missing timer or interrupt-controller source files.
- `sw/buildroot` selects `hello-mmio-smoke`, and the smoke checks the public
  Linux driver surface instead of `/dev/mem`.
- QEMU and Renode remain reference-only; Chipyard is the generated-AP handoff;
  CVA6 remains an alternate blocked path.

## Remaining Boot Blockers

These cannot be closed by editing repository metadata alone:

- Generate or import `build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`.
- Build the generated Chipyard Verilator simulator.
- Provide an OpenSBI/Linux payload accepted by `scripts/locate_chipyard_linux_payload.py`.
- Run `scripts/run_chipyard_openphone_linux_smoke.sh` on a Linux host/container.
- Archive real transcripts with `scripts/capture_chipyard_linux_evidence.sh all`.
- Re-run `python3 scripts/check_cpu_ap_evidence.py --require-evidence`.

QEMU virt and Renode logs can validate payload plumbing only. They do not close
the hello-chip or generated-AP Linux evidence gates.
