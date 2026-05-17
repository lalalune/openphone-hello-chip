# CPU/AP blocker status

Date: 2026-05-17

Scope: `rtl/cpu/**`, CPU-facing contract tests, and project CPU/AP status.

## Current Local Artifact

The only in-repo executable CPU artifact is
`rtl/cpu/hello_cpu_subsystem_stub.sv`. Despite the legacy module name, it is a
tiny hand-written RV-style contract CPU, not a Linux-capable application
processor.

Locally proven by `make cocotb-cpu`:

- reset identity is exposed as `RESET_PC=0x8000_0000` and `HART_ID=0` in the
  CPU contract wrapper,
- fetch starts at the reset boundary,
- the tiny CPU executes the documented small integer/load/store/control-flow
  subset,
- unsupported, privileged, CSR, unaligned, and bus-error paths halt
  fail-closed,
- timer, software, and external interrupt inputs are pending-level placeholders
  only.

Not proven:

- RV64GC compliance,
- CSR/trap behavior,
- M/S/U privilege modes,
- interrupt or exception entry/return,
- CLINT/ACLINT timer/software interrupt compatibility,
- PLIC/IMSIC compatibility beyond the local claim/complete scaffold,
- MMU, page-table walks, caches, atomics, compressed instructions, floating
  point, or coherent memory,
- boot ROM execution, OpenSBI handoff, Linux boot, Android boot, UART console,
  or generated DTS consistency.

## Selected Open CPU/AP Path

The selected path is a generated Chipyard Rocket RV64GC subsystem. The selection
is pinned in `generators/chipyard/openphone-rocket-manifest.json`:

- Chipyard `1.13.0`, commit
  `69eba860a352343e4ac6b6df0f3638a79a86ec78`,
- single Rocket RV64GC hart for first AP integration,
- project config name `OpenPhoneRocketConfig`,
- production wrapper name `openphone_rocket_ap`,
- generated import manifest expected at
  `build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json`.

No generated Chipyard/Rocket RTL, simulator, DTS, firmware image, or boot log is
present in this repository yet. Therefore the CPU/AP path is blocked on external
generator integration, not on more hand-written tiny-CPU expansion.

## Host Checks

- `make chipyard-generator-check` verifies the selected AP path is pinned and
  non-claiming.
- `make chipyard-generated-check` is expected to fail until generated artifacts
  exist, the generated import manifest records recursive submodules, commands,
  tool versions, artifact paths, and SHA-256 values, and those paths validate
  against `docs/evidence/cpu-ap-evidence-manifest.json`.
- `make cpu-ap-evidence-check` is expected to fail until real OpenSBI/Linux and
  trap/timer/IRQ evidence logs exist. Archive real external transcripts with
  `python3 scripts/capture_cpu_ap_evidence.py intake ...`; the helper only
  accepts logs containing the manifest-required AP boot/trap markers.
- `make cpu-ap-completion-gate` stays blocked until the selected manifest makes
  a real AP claim and the generated artifacts plus transcripts validate.
- `sw/platform/hello_platform_contract.json` must remain `has_cpu=false` until
  generated CPU/AP artifacts and boot evidence exist.
