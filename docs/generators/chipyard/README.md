# Chipyard Rocket AP Import

This directory records the selected real CPU/AP integration path. It is not
Linux boot evidence by itself.

The pinned path is Chipyard `1.13.0` at commit
`69eba860a352343e4ac6b6df0f3638a79a86ec78`, using a single Rocket RV64GC hart
in a project config named `OpenPhoneRocketConfig`.

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
recursive submodule state:

```sh
python3 scripts/check_chipyard_import_preflight.py --require-checkout
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
