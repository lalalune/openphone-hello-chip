# Hello demo package contract

Evidence class: `non_release_placeholder`
Release use: `prohibited`

The demo product target is a Placeholder package using a QFN64-style planning package for review and PCB bring-up flow validation only.

This is not vendor package data, not a foundry-approved package, not a bond diagram, and not a footprint source. It exists to make the top-level chip interface explicit while the project uses open PDK digital flows.

## Package assumptions

- 64 pins.
- `3.3 V` IO domain.
- `1.8 V` core domain.
- External clock input.
- Active-low reset input.
- Parallel debug/MMIO demo interface for board smoke tests.
- GPIO LED outputs.
- IRQ test-point outputs.
- JTAG pins reserved for future scan/debug.

## Release blockers

- Package-vendor drawing is missing.
- Shuttle/package approval evidence is missing.
- Bond diagram mapping die pads to package pins is missing.
- Package electrical/parasitic model is missing.
- Package-vendor footprint evidence is missing.

Before fabrication, this document must be replaced by the actual shuttle/package/bonding document and actual shuttle/package/bonding evidence. Do not use this file as release evidence.

## KiCad release dependency

Do not derive a fabrication-ready KiCad project, footprint, or Gerber package
from this placeholder package contract. Board release requires a vendor package
drawing, package source checksum or immutable revision, land-pattern review,
bond diagram, and package-pin to board-net cross-probe before any KiCad outputs
can be treated as manufacturing evidence.
