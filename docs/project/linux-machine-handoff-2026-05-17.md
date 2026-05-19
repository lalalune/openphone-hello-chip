# Linux machine handoff

Date: 2026-05-17

Purpose: prepare a Linux host to test the generated AP/AOSP path without
turning qemu-virt or Cuttlefish reference evidence into an OpenAgent chip claim.

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

This is only `qemu_virt_reference_only_not_e1_chip_rtl` evidence.

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
scripts/run_chipyard_openagent_verilator.sh verilog
python3 scripts/check_chipyard_generator_manifest.py --require-generated
python3 scripts/check_chipyard_generated_linux_contract.py
python3 scripts/check_chipyard_payload_path.py
```

Generated Verilog, DTS, simulator paths, tool versions, commands, and SHA-256
values must be recorded in
`build/chipyard/openagent_rocket/OpenAgentRocketConfig.manifest.json`.

4. Run a generated AP OpenSBI/Linux smoke:

```sh
python3 scripts/locate_chipyard_linux_payload.py --json
eval "$(python3 scripts/locate_chipyard_linux_payload.py --export-env)"
scripts/run_chipyard_openagent_linux_smoke.sh
python3 scripts/check_chipyard_verilator_linux_smoke.py
```

The preferred first payload is the FireMarshal no-disk boot ELF at
`external/chipyard/software/firemarshal/images/firechip/linux-poweroff/linux-poweroff-bin-nodisk`.
It is a RISC-V ELF boot binary with OpenSBI content and a Linux initramfs
workload, which is the format Chipyard `run-binary` expects for this smoke.
If it is missing on the Linux host, build it with:

```sh
cd external/chipyard/software/firemarshal
./marshal -v -d build example-workloads/linux-poweroff.json
cd -
python3 scripts/locate_chipyard_linux_payload.py --require
```

This is the first gate that can start closing an OpenAgent generated-AP Linux
claim.

If `check_chipyard_verilator_linux_smoke.py` reports stale `/work/` or other
container paths in `VTestDriver.mk`, regenerate the simulator on the Linux host
or run inside the same container mount path that produced the generated
artifacts. Do not patch the generated makefile by hand and call it evidence.
The native wrappers now run this cleanup before invoking Chipyard:

```sh
python3 scripts/check_chipyard_verilator_linux_smoke.py --repair-stale-generated
```

That command removes only the generated Verilator config directory and simulator
binary when the generated driver makefile or filelists contain stale
container/workspace absolute paths. It does not alter checked-in source or
create boot evidence. The next
`scripts/run_chipyard_openagent_verilator.sh ...` or native
`scripts/run_chipyard_openagent_linux_smoke.sh` invocation must then regenerate
the driver makefile on the current host. On macOS/arm64, prefer the container
smoke path so the generated `/work/...` paths match the container mount:

```sh
CHIPYARD_LINUX_SMOKE_USE_DOCKER=1 scripts/run_chipyard_openagent_linux_smoke.sh
```

5. Archive CPU/AP evidence:

```sh
python3 scripts/wire_cpu_ap_capture_commands.py --format text
eval "$(python3 scripts/wire_cpu_ap_capture_commands.py --format shell)"
scripts/capture_chipyard_linux_evidence.sh preflight
```

The wiring helper derives `OPENAGENT_OPENSBI_BOOT_CMD` and
`OPENAGENT_LINUX_BOOT_CMD` from the generated AP Linux smoke runner when the
payload and generated manifest are present. It does not invent the
trap/timer/IRQ, ISA/cache/MMU, or benchmark commands; those must be real
generated-target tests and must remain blocked until supplied.

After the preflight reports all command lanes ready, use the wrapper to run
each generated-target capture command and intake the accepted transcript:

```sh
scripts/capture_chipyard_linux_evidence.sh all
python3 scripts/check_cpu_ap_evidence.py --require-evidence
```

or archive already-captured serial/test logs one by one:

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
AOSP_DIR=/path/to/aosp make aosp-linux-preflight
AOSP_DIR=/path/to/aosp make aosp-linux-handoff-build-only
AOSP_DIR=/path/to/aosp make aosp-linux-handoff
python3 scripts/check_android_sim_boot.py
python3 scripts/check_software_bsp.py aosp --require-evidence
```

`aosp-linux-preflight` writes
`build/reports/aosp_linux_preflight.json` with separate import, build,
Cuttlefish, CTS/VTS intake, QEMU, and Renode tracks. On a host that only has
the modern Cuttlefish command, set `AOSP_CUTTLEFISH_LAUNCHER=cvd`; otherwise
the scripts prefer `launch_cvd` and fall back to `cvd start`.

`aosp-linux-handoff-build-only` is the bounded first pass: it imports the
device tree and captures lunch/vendorimage/VINTF/SELinux evidence, then stops
before simulator and CTS/VTS work. `aosp-linux-handoff` attempts the full
virtual-device sequence and keeps failing until real transcripts satisfy
`docs/android/bsp-log-evidence-manifest.json`.

Cuttlefish remains Android reference evidence unless it is tied to the
generated OpenAgent AP simulator by a separate manifest-bound transcript.

7. Re-run the top-level handoff/MVP checks:

```sh
make linux-handoff-check
python3 scripts/run_mvp_simulator.py
python3 scripts/check_mvp_simulator.py
```

The MVP report may claim `on_chip_os_boot_claim=true` only when the
`chipyard_verilator_linux_smoke` and CPU/AP evidence gates pass. A passing
qemu-virt Linux boot only sets `reference_qemu_virt_os_boot_claim=true`.
