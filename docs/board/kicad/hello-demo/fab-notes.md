# Hello demo KiCad planning notes

Evidence class: `non_release_demo_planning`
Release use: `prohibited`

`board/kicad/hello-demo` now contains a minimal KiCad project, schematic, PCB,
and planning footprint so the package pinout can be cross-probed and the board
can be opened or printed for review. These sources are planning artifacts only.
They are not board fabrication evidence and are not a substitute for a vendor
land pattern, clean ERC/DRC, Gerbers, drill output, BOM, placement files,
assembly package, or DFM review.

Current KiCad evidence status:

- KiCad project source: `board/kicad/hello-demo/hello-demo.kicad_pro`.
- Planning schematic source: `board/kicad/hello-demo/hello-demo.kicad_sch`.
- Planning PCB source: `board/kicad/hello-demo/hello-demo.kicad_pcb`.
- Planning footprint source:
  `board/kicad/hello-demo/hello_demo_planning.pretty/hello_demo_qfn64_planning.kicad_mod`.
- No Gerber, drill, BOM, position, fab drawing, ERC, DRC, or command transcript outputs are checked in.
- `package/hello-demo-pinout.yaml` is a placeholder planning pinout and is not sufficient to generate fabrication-ready KiCad artifacts.
- Required command capture and artifact manifests are documented in
  `board/kicad/hello-demo/artifact-manifest.yaml`.

Fabrication blockers:

- Package is placeholder-only.
- Footprint is not derived from a package vendor drawing.
- No package drawing checksum or immutable revision is recorded.
- No bond diagram has been released.
- Power sequencing and decoupling values are preliminary.
- No SI/PI analysis has been performed.
- No assembly house DFM review has been performed.
- No checked schematic, PCB, Gerbers, drill files, BOM, or placement files exist in this directory.
- Power sequencing and decoupling values are preliminary.
- No SI/PI analysis has been performed.
- No assembly house DFM review has been performed.

Bring-up intent:

1. Current-limit both rails.
2. Confirm `1.8 V` and `3.3 V` rails.
3. Confirm external clock.
4. Release reset.
5. Read ROM ID over debug bus.
6. Toggle GPIO LEDs.
7. Run NPU add smoke command.
8. Observe IRQ outputs.
