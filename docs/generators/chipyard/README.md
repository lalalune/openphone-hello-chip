# Chipyard Rocket AP Import

This directory records the selected real CPU/AP integration path. It is not
Linux boot evidence by itself.

The pinned path is Chipyard `1.13.0` at commit
`69eba860a352343e4ac6b6df0f3638a79a86ec78`, using a single Rocket RV64GC hart
in a project config named `OpenPhoneRocketConfig`.

The repo-local config source is:

```text
generators/chipyard/openphone/src/main/scala/openphone/OpenPhoneRocketConfig.scala
```

`scripts/bootstrap_chipyard.sh` installs that overlay into the pinned checkout at
`external/chipyard/generators/chipyard/src/main/scala/openphone/OpenPhoneRocketConfig.scala`.
It refuses to overwrite a different file at that destination.

This is a first Linux bring-up target, not a 2028 phone-class AP. Phone-class
claims remain blocked until a separate target boundary supplies topology, ISA
profile, cache/coherency, MMU, benchmark, power/thermal, Android, and silicon
evidence.

## Local Checks

Check the selected path without a Chipyard checkout:

```sh
python3 scripts/check_chipyard_generator_manifest.py
```

Record a lightweight bootstrap/import preflight without cloning or building if
`external/chipyard` is absent:

```sh
python3 scripts/check_chipyard_import_preflight.py
```

Require an already-bootstrapped checkout to match the pinned tag, commit, and
recursive submodule state, and to contain the installed OpenPhoneRocketConfig
overlay:

```sh
python3 scripts/check_chipyard_import_preflight.py --require-checkout
```

Check the Chipyard environment needed to build the OpenPhoneRocketConfig
Verilator simulator without modifying the checkout:

```sh
python3 scripts/check_chipyard_verilator_preflight.py
```

When that preflight passes, the expected build command is:

```sh
cd external/chipyard/sims/verilator
source ../../env.sh
make CONFIG=OpenPhoneRocketConfig CONFIG_PACKAGE=openphone
```

The guarded repo wrapper runs the same preflight first and refuses to invoke
Chipyard make while setup blockers remain:

```sh
scripts/run_chipyard_openphone_verilator.sh
```

Require generated artifacts and evidence:

```sh
make chipyard-generated-check cpu-ap-evidence-check cpu-ap-completion-gate
```

Archive real external transcripts after the generated AP run:

```sh
python3 scripts/capture_cpu_ap_evidence.py intake linux-boot \
  --source /path/to/linux-serial.log \
  --command '/exact/external/boot command'
python3 scripts/capture_cpu_ap_evidence.py intake isa-cache-mmu \
  --source /path/to/isa-cache-mmu.log \
  --command '/exact/external/isa-cache-mmu command'
python3 scripts/capture_cpu_ap_evidence.py intake ap-benchmarks \
  --source /path/to/ap-benchmarks.log \
  --command '/exact/external/benchmark command'
python3 scripts/capture_cpu_ap_evidence.py hashes
```

Generated Verilog must not be hand-edited. It should be copied or symlinked into
the eventual RTL wrapper location only through documented import steps so RTL
regressions remain reproducible.

## Local Manifests

- `openphone-rocket-manifest.json` is the repo-local selection gate. It must
  remain `selected_not_generated` until generated RTL, DTS, simulator, firmware
  inputs, and boot/trap evidence exist.
- `import-manifest.template.json` is copied into
  `build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json` by the
  eventual generator/import flow, then filled with recursive submodule SHAs,
  command lines, tool versions, artifact paths, artifact SHA-256 values,
  evidence paths, and evidence SHA-256 values.
- `docs/evidence/cpu-ap-evidence-manifest.json` is the fail-closed schema for
  generated artifact paths and required OpenSBI/Linux/trap transcript markers.
  Its `linux_capable_gate_matrix` keeps RV64GC ISA, S-mode privilege, Sv39 MMU,
  CLINT/ACLINT timer/software IRQ, PLIC external IRQ, UART, DTB, OpenSBI
  handoff, and Linux initramfs smoke gates in `blocked` state until real
  generated-target evidence is archived.
- `scripts/run_qemu.sh --check-os` writes
  `build/reports/qemu_os_boot_attempt.log` with `BLOCKED`, `FAIL`, or `PASS`.
  That log is software-reference evidence only; it cannot close any
  Chipyard/Rocket AP Linux-capable gate.

## First Integration Target

```text
OpenPhoneRocketConfig
1x Rocket RV64GC hart
CLINT/ACLINT-compatible mtime, mtimecmp, and msip
PLIC-compatible external interrupts
UART for firmware and Linux early console
DRAM model sized for OpenSBI + Linux initramfs smoke
hello DMA/NPU/display/peripheral MMIO attachment points
generated DTS checked against the platform contract
```
