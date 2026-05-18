# MacBook Blocker Ledger - 2026-05-17

This ledger records the blockers closed locally on the MacBook and the blockers that remain fail-closed because they require target hardware, Linux-hosted EDA runs, FPGA toolchains, foundry/vendor artifacts, or physical review evidence.

## Closed locally

| Workstream | Evidence | Gate |
| --- | --- | --- |
| Benchmark MVP evidence | `benchmarks/results/final-macbook-host-smoke/report.json` is now preferred by the MVP status gate when present. | `make mvp-status` reports `benchmarks` as `PASS`. |
| KiCad CLI availability | KiCad 10.0.2 was fetched and run from the mounted DMG without requiring privileged install. | `board/reports/fab/hello-demo-2026-05-17/kicad-tool-versions.txt` |
| KiCad fabrication artifacts | ERC, DRC, Gerbers, drill, BOM, position CSV, fab drawing PDF, and command transcript were generated. | `python3 scripts/check_kicad_artifacts.py` passes. |
| KiCad manifest bookkeeping | `board/kicad/hello-demo/artifact-manifest.yaml` now tracks generated CLI outputs as draft evidence instead of missing evidence. | `python3 scripts/check_manufacturing_artifacts.py --manifest board/kicad/hello-demo/artifact-manifest.yaml` passes. |
| Product scaffold integrity | Non-release product package checks remain consistent with fail-closed release gates. | `make product-check` passes. |
| Project pipeline | The normal artifact pipeline remains green after the local evidence updates. | `python3 scripts/pipeline_check.py` passes. |

## Still blocked

| Workstream | Current blocker | Why it is not closed locally |
| --- | --- | --- |
| Software BSP | `software-bsp` remains blocked in `make mvp-status`. | Requires external Buildroot/Linux/AOSP evidence imports and target boot logs, not just local scaffolds. |
| KiCad board release | `scripts/check_kicad_artifacts.py --release` fails. | ERC report is not clean, source metadata/checksums are incomplete, and DFM/stackup/package-board/SI/PI/current reviews are missing. |
| FPGA release | `scripts/check_fpga_release.py --release` fails. | Exact board revision is unassigned and no bitstream, nextpnr timing/route report, ecppack transcript, or FPGA tool-version evidence exists. |
| Physical design signoff | `scripts/check_pd_signoff.py` fails release. | No complete routed OpenLane/OpenROAD run contains all required GDS/DEF/netlist/timing/DRC/LVS/antenna/STA/congestion/fill/tool-version artifacts. |
| Manufacturing/package evidence | `scripts/check_manufacturing_artifacts.py --release` fails. | Vendor package drawing, bond diagram, footprint-source checksum, padframe-board cross-probe, SI/PI/current/thermal evidence, and release reviews are absent. |
| Product release | `make product-release-check` fails. | Aggregates the still-blocked KiCad, FPGA, PD, manufacturing, and placeholder fab-note release gates. |
| Strict target benchmarks | Strict benchmark mode still blocks on real target tools/metadata/NNAPI evidence. | Host-smoke metrics are useful MVP evidence but are not accepted as target performance proof. |

## Next MacBook-reducible tasks

1. Fix the schematic ERC violations in `board/reports/fab/hello-demo-2026-05-17/hello-demo-erc-report.txt`.
2. Generate source checksum metadata for the KiCad sources after ERC is clean.
3. Add board review templates that can be filled by a real reviewer without changing release gates to complete.
4. Run a complete OpenLane/OpenROAD smoke flow only if the pinned tool/PDK environment is available locally.
5. Keep `make product-release-check` fail-closed until every release artifact above exists and is reviewed.
