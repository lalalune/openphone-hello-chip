# Hello demo KiCad command capture plan

No KiCad project is currently checked in. These commands are the required
headless transcript plan once a real `board/kicad/hello-demo/*.kicad_pro`,
`*.kicad_sch`, `*.kicad_pcb`, symbol library, and footprint library exist.

The commands must be run from the repository root and captured in
`board/reports/fab/command-transcript-<rev>.txt` with matching
`board/reports/fab/tool-versions-<rev>.txt`. Do not create the report
directory as release evidence until the inputs are real and reviewed.

```sh
kicad-cli version
kicad-cli sch erc board/kicad/hello-demo/hello-demo.kicad_sch --output board/reports/fab/erc-hello-demo.txt
kicad-cli pcb drc board/kicad/hello-demo/hello-demo.kicad_pcb --output board/reports/fab/drc-hello-demo.txt
kicad-cli pcb export gerbers board/kicad/hello-demo/hello-demo.kicad_pcb --output board/reports/fab/gerbers
kicad-cli pcb export drill board/kicad/hello-demo/hello-demo.kicad_pcb --output board/reports/fab/drill
kicad-cli sch export bom board/kicad/hello-demo/hello-demo.kicad_sch --output board/reports/fab/bom-hello-demo.csv
kicad-cli pcb export pos board/kicad/hello-demo/hello-demo.kicad_pcb --output board/reports/fab/position-hello-demo.csv
kicad-cli pcb export pdf board/kicad/hello-demo/hello-demo.kicad_pcb --output board/reports/fab/fab-drawing-hello-demo.pdf
```

Release capture must also include:

- Package vendor drawing checksum or immutable revision.
- KiCad symbol and footprint source review.
- Cross-probe report for package pins, KiCad pins, footprint pads, and board nets.
- Stackup, SI/PI, PDN/current-budget, and DFM evidence referenced by
  `docs/manufacturing/release-manifest.yaml`.
