# hello_chip_top OpenLane Progress Report - 2026-05-17

## Scope

This report records local MacBook physical-design evidence for exploratory
SKY130 OpenLane runs of the full `hello_chip_top`. It is progress evidence, not
release or tapeout signoff.

## Run

- Run directory: `pd/openlane/runs/RUN_2026-05-18_04-00-56`
- Flow config: `pd/openlane/config.sky130.json`
- Design: `hello_chip_top`
- Runner image: `ghcr.io/efabless/openlane2:2.4.0.dev1`
- Run status observed: reached `KLayout.DRC`; no `final/` directory was
  produced because `64-klayout-drc/state_out.json` was not written.
- The immediately preceding wider run
  `pd/openlane/runs/RUN_2026-05-18_03-48-01` reached
  `OpenROAD.RepairDesignPostGPL` but did not produce final signoff artifacts.

## Evidence Produced

- Verilator lint ran and reported no lint errors, with 444 lint warnings.
- Yosys synthesis completed with no unmapped-cell or synthesis-check failures.
- Floorplan, PDN generation, IO placement, global placement, CTS, timing
  repair, global routing, antenna checks, detailed routing, RC extraction,
  post-PnR STA, IR-drop reporting, Magic/KLayout streamout, LEF generation,
  XOR, and Magic DRC ran.
- Detailed routing completed with zero final routing violations after
  optimization.
- Magic DRC reported zero errors.
- XOR check reported no differences.
- OpenROAD IR-drop report completed, with the usual warning that `VSRC_LOC_FILES`
  was not supplied.
- KLayout DRC ran for 7m57s, peaked at 6 GiB RSS, and stopped without a
  `state_out.json`; this is the current reproducible PD closure blocker.
- Global placement and detailed routing produced `hello_chip_top.odb`, DEF,
  netlists, SDC, and OpenROAD metrics under their respective step directories.
- Non-release OpenLane preflight passed:

```text
python3 scripts/check_openlane_run_preflight.py
OpenLane run preflight passed.
```

## Key Metrics

- Config target: 100 ns clock period, 3.2 mm x 3.2 mm die, 2.88 mm x 2.88 mm
  core.
- Global-placement instance count: 155,197 total instances.
- Post-CTS/timing-repair instance count: 162,146 total instances.
- Detailed-routing instance count: 206,974 total instances, including 44,828
  antenna cells and 5,317 timing repair buffers.
- Detailed-routing standard-cell utilization: 8.63733%.
- Core area: 8,286,800 square microns.
- Die area: 10,240,000 square microns.
- Detailed-route wire length: 2,892,171 um.
- Detailed-route vias: 443,312.
- Detailed route final DRT violations: 0.
- Post-CTS timing: setup violation count 0 at the 100 ns trial target; hold
  violations remain before full signoff closure.
- IR-drop report: worst VPWR drop 0.00013935 V; worst VGND drop 0.000145911 V.
- Detailed-routing peak RSS: 3 GiB.
- KLayout DRC peak RSS: 6 GiB.

## Release Blockers

- No complete signoff `hello_chip_top` run exists because the best run stopped
  at KLayout DRC.
- No `final/gds`, `final/def`, final SPEF/SDF, clean KLayout DRC report,
  complete LVS report, or complete release manifest exists for `hello_chip_top`.
- KLayout DRC must complete and produce `state_out.json` plus a release-readable
  clean report.
- Top-level antenna metadata warnings remain:
  4 input pins without antenna gate information and 2 output pins without
  antenna diffusion information.
- High-fanout generated nets with 100+ pins slow detailed routing and should be
  named, constrained, buffered, or structurally reduced.
- Release OpenLane configs are still exploratory and intentionally fail release
  preflight because fail-closed timing/DRC/LVS/slew gates are not enabled.
- The PD signoff manifest remains blocked for package, SI/PI, PDN/current,
  thermal, padframe, and board fabrication evidence.

## Reproduction

```bash
OPENLANE_TIMEOUT_SECONDS=21600 scripts/run_openlane.sh
python3 scripts/check_openlane_run_preflight.py
python3 scripts/check_openlane_run_preflight.py --release
python3 scripts/check_pd_signoff.py
```

The timeout wrapper is intentionally supported for MacBook runs so incomplete
long-running OpenLane jobs end with explicit exit code `124` instead of an
ambiguous abandoned process.

The launcher also creates `.openlane-run.lock` to prevent concurrent duplicate
OpenLane runs from competing for memory and invalidating local evidence.
