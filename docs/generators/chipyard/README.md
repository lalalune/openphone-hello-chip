# Chipyard Rocket AP path

This directory records the selected real CPU/AP integration path. It is not
Linux boot evidence by itself.

The pinned path is Chipyard `1.13.0` at commit
`69eba860a352343e4ac6b6df0f3638a79a86ec78`, using a single Rocket RV64GC hart
in a project config named `OpenPhoneRocketConfig`.

## Local Manifests

- `openphone-rocket-manifest.json` is the repo-local selection gate. It must
  remain `selected_not_generated` until generated RTL, DTS, simulator, firmware
  inputs, and boot/trap evidence exist.
- `import-manifest.template.json` is copied into
  `build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json` by the
  eventual generator/import flow, then filled with recursive submodule SHAs,
  command lines, tool versions, artifact paths, and evidence paths.

Check the selected path without a Chipyard checkout:

```sh
make chipyard-generator-check
```

Require generated artifacts and evidence:

```sh
make chipyard-generated-check
```

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

Generated Verilog must not be hand-edited. It should be copied or symlinked into
the eventual RTL wrapper location only through documented Make targets so RTL
regressions remain reproducible.
