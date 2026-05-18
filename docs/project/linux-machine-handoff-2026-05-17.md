# Linux machine handoff

Date: 2026-05-17

Purpose: prepare a Linux host to test the generated AP/AOSP path without
turning qemu-virt or Cuttlefish reference evidence into an OpenPhone chip claim.

## Current host-independent checks

Run this first after checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
make linux-handoff-check
```

`make linux-handoff-check` writes `build/reports/linux_handoff_check.log`.
Required regression checks must pass. External integration gates may report
`BLOCKED`; that is the expected state until the Linux host has Chipyard,
generated AP artifacts, AOSP, and boot transcripts.

## Linux host prerequisites

Install the normal repo tools plus the heavy external stack:

- Docker or native Chipyard dependencies.
- Conda for Chipyard setup.
- Java, make, Verilator, and `firtool`.
- RISC-V toolchain with `RISCV` exported by `external/chipyard/env.sh`.
- QEMU `qemu-system-riscv64`.
- AOSP checkout if Android evidence is being attempted.
- Cuttlefish/KVM and `adb` for Android virtual-device evidence.

The macOS host can validate scripts and qemu-virt reference boot. It cannot run
local Cuttlefish/KVM and does not currently have the Chipyard generated AP
environment.

## Bring-up order on Linux

1. Verify qemu-virt reference payload plumbing:

```sh
python3 scripts/fetch_qemu_linux_payload.py
QEMU_OS_BOOT_SECONDS=30 scripts/run_qemu.sh --check-os
python3 scripts/check_qemu_linux_payload_status.py
```

This is only `qemu_virt_reference_only_not_hello_chip_rtl` evidence.

2. Prepare Chipyard:

```sh
scripts/bootstrap_chipyard.sh
cd external/chipyard
./build-setup.sh --use-lean-conda --skip-firesim --skip-marshal
cd -
python3 scripts/check_chipyard_verilator_preflight.py
```

If the full Chipyard setup requires different skip flags on the Linux machine,
record the exact command in the preflight report before claiming generated AP
readiness.

3. Generate the selected AP simulator artifacts:

```sh
scripts/run_chipyard_openphone_verilator.sh verilog
python3 scripts/check_chipyard_generator_manifest.py --require-generated
python3 scripts/check_chipyard_payload_path.py
```

Generated Verilog, DTS, simulator paths, tool versions, commands, and SHA-256
values must be recorded in
`build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`.

4. Run a generated AP OpenSBI/Linux smoke:

```sh
export CHIPYARD_LINUX_BINARY=/path/to/real/opensbi-or-linux-payload.elf
cd external/chipyard/sims/verilator
source ../../env.sh
make CONFIG=OpenPhoneRocketConfig CONFIG_PACKAGE=openphone \
  BINARY="$CHIPYARD_LINUX_BINARY" LOADMEM=1 run-binary \
  2>&1 | tee ../../../../build/chipyard/openphone_rocket/verilator-linux-smoke.log
cd -
python3 scripts/check_chipyard_verilator_linux_smoke.py
```

This is the first gate that can start closing an OpenPhone generated-AP Linux
claim.

5. Archive CPU/AP evidence:

```sh
python3 scripts/capture_cpu_ap_evidence.py intake opensbi-boot \
  --source /path/to/opensbi-serial.log \
  --command '/exact command'
python3 scripts/capture_cpu_ap_evidence.py intake linux-boot \
  --source /path/to/linux-serial.log \
  --command '/exact command'
python3 scripts/capture_cpu_ap_evidence.py intake trap-timer-irq \
  --source /path/to/trap-timer-irq.log \
  --command '/exact command'
python3 scripts/capture_cpu_ap_evidence.py intake isa-cache-mmu \
  --source /path/to/isa-cache-mmu.log \
  --command '/exact command'
python3 scripts/capture_cpu_ap_evidence.py intake ap-benchmarks \
  --source /path/to/ap-benchmarks.log \
  --command '/exact command'
python3 scripts/check_cpu_ap_evidence.py --require-evidence
```

6. Attempt AOSP evidence on Linux:

```sh
AOSP_DIR=/path/to/aosp scripts/boot_android_simulator.sh \
  --run-cuttlefish --run-cts --run-vts
python3 scripts/check_android_sim_boot.py
python3 scripts/check_software_bsp.py aosp --require-evidence
```

Cuttlefish remains Android reference evidence unless it is tied to the generated
OpenPhone AP simulator by a separate manifest-bound transcript.

7. Re-run the top-level handoff/MVP checks:

```sh
make linux-handoff-check
python3 scripts/run_mvp_simulator.py
python3 scripts/check_mvp_simulator.py
```

The MVP report may claim `on_chip_os_boot_claim=true` only when the
`chipyard_verilator_linux_smoke` and CPU/AP evidence gates pass. A passing
qemu-virt Linux boot only sets `reference_qemu_virt_os_boot_claim=true`.

