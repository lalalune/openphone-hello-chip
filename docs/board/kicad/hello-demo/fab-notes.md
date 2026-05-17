# Hello demo KiCad placeholder notes

Evidence class: `non_release_placeholder`
Release use: `prohibited`

This directory is reserved for the KiCad project once package-vendor data and the pinout contract are stable. These notes are not board fabrication evidence and are not a substitute for a KiCad project, footprint, fab package, assembly package, or DFM review.

Current KiCad evidence status:

- No KiCad project, schematic, PCB, symbol library, or footprint library is checked in.
- No Gerber, drill, BOM, position, fab drawing, ERC, DRC, or command transcript outputs are checked in.
- `package/hello-demo-pinout.yaml` is a placeholder planning pinout and is not sufficient to generate fabrication-ready KiCad artifacts.
- Required command capture and artifact manifests are documented in `docs/board/kicad/hello-demo-commands.md` and `docs/board/kicad/hello-demo-artifact-manifest.yaml`.

Fabrication blockers:

- Package is placeholder-only.
- Footprint is not derived from a package vendor drawing.
- No package drawing checksum or immutable revision is recorded.
- No bond diagram has been released.
- Power sequencing and decoupling values are preliminary.
- No SI/PI analysis has been performed.
- No assembly house DFM review has been performed.
- No checked schematic, PCB, Gerbers, drill files, BOM, or placement files exist in this directory.

Bring-up intent:

1. Current-limit both rails.
2. Confirm `1.8 V` and `3.3 V` rails.
3. Confirm external clock.
4. Release reset.
5. Read ROM ID over debug bus.
6. Toggle GPIO LEDs.
7. Run NPU add smoke command.
8. Observe IRQ outputs.
