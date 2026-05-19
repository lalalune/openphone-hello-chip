# PD Signoff Archive Report

This report is generated evidence for a selected OpenLane run. It is not
a release approval unless `release_ready` is `true` and the normal PD
signoff checks also pass.

- Generated at: `2026-05-19T02:47:15Z`
- Run directory: `pd/openlane/runs/RUN_2026-05-19_01-52-14`
- Archive directory: `build/pd-signoff-archives/RUN_2026-05-19_01-52-14`
- Last completed OpenLane step: `42-odb-heuristicdiodeinsertion`
- Release ready: `false`

## Artifact Classes

| Class | Status | Source | Files copied | Missing / dirty evidence |
|---|---:|---|---:|---|
| `run_manifest` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `gds` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `def` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `gate_netlist` | `present` | `fallback` | 1 | - |
| `corner_manifest` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `sdc` | `present` | `fallback` | 1 | - |
| `spef` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `sdf` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `drc_report` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `klayout_drc_report` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `lvs_report` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `antenna_report` | `blocked` | `fallback` | 3 | missing clean marker: pd/openlane/runs/RUN_2026-05-19_01-52-14/38-openroad-globalrouting/antenna.rpt, pd/openlane/runs/RUN_2026-05-19_01-52-14/39-openroad-checkantennas/reports/antenna.rpt, pd/openlane/runs/RUN_2026-05-19_01-52-14/39-openroad-checkantennas/reports/antenna_summary.rpt |
| `sta_report` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `utilization_report` | `blocked` | `fallback` | 1 | missing clean marker: pd/openlane/runs/RUN_2026-05-19_01-52-14/06-yosys-synthesis/reports/stat.rpt |
| `congestion_report` | `blocked` | `fallback` | 1 | missing clean marker: pd/openlane/runs/RUN_2026-05-19_01-52-14/38-openroad-globalrouting/or_metrics_out.json |
| `density_fill_report` | `missing` | `missing` | 0 | no matching manifest or fallback artifacts |
| `tool_versions` | `present` | `fallback` | 2 | - |

## Flow State

Steps missing `state_out.json`:
- `43-openroad-repairantennas`

## Copied Files

### gate_netlist
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/06-yosys-synthesis/e1_chip_top.nl.v` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/gate_netlist/06-yosys-synthesis/e1_chip_top.nl.v`

### sdc
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/34-openroad-cts/e1_chip_top.sdc` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/sdc/34-openroad-cts/e1_chip_top.sdc`

### antenna_report
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/38-openroad-globalrouting/antenna.rpt` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/antenna_report/38-openroad-globalrouting/antenna.rpt`
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/39-openroad-checkantennas/reports/antenna.rpt` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/antenna_report/39-openroad-checkantennas/reports/antenna.rpt`
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/39-openroad-checkantennas/reports/antenna_summary.rpt` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/antenna_report/39-openroad-checkantennas/reports/antenna_summary.rpt`

### utilization_report
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/06-yosys-synthesis/reports/stat.rpt` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/utilization_report/06-yosys-synthesis/reports/stat.rpt`

### congestion_report
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/38-openroad-globalrouting/or_metrics_out.json` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/congestion_report/38-openroad-globalrouting/or_metrics_out.json`

### tool_versions
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/flow.log` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/tool_versions/flow.log`
- `pd/openlane/runs/RUN_2026-05-19_01-52-14/resolved.json` -> `build/pd-signoff-archives/RUN_2026-05-19_01-52-14/artifacts/tool_versions/resolved.json`
