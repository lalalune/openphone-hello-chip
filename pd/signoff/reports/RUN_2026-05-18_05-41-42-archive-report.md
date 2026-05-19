# PD Signoff Archive Report

This report is generated evidence for a selected OpenLane run. It is not
a release approval unless `release_ready` is `true` and the normal PD
signoff checks also pass.

- Generated at: `2026-05-19T01:40:10Z`
- Run directory: `pd/openlane/runs/RUN_2026-05-18_05-41-42`
- Archive directory: `build/pd-signoff-archives/RUN_2026-05-18_05-41-42`
- Last completed OpenLane step: `76-misc-reportmanufacturability`
- Release ready: `false`

## Artifact Classes

| Class | Status | Source | Files copied | Missing / dirty evidence |
|---|---:|---|---:|---|
| `run_manifest` | `present` | `manifest` | 1 | - |
| `gds` | `present` | `manifest` | 1 | - |
| `def` | `present` | `manifest` | 1 | - |
| `gate_netlist` | `present` | `manifest` | 1 | - |
| `corner_manifest` | `present` | `manifest` | 1 | - |
| `sdc` | `present` | `manifest` | 1 | - |
| `spef` | `present` | `manifest` | 3 | - |
| `sdf` | `present` | `manifest` | 9 | - |
| `drc_report` | `blocked` | `manifest` | 2 | missing clean marker: pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/drc_klayout.rpt, pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/drc_magic.rpt |
| `lvs_report` | `present` | `manifest` | 1 | - |
| `antenna_report` | `blocked` | `manifest` | 1 | missing clean marker: pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/antenna.rpt |
| `sta_report` | `blocked` | `manifest` | 1 | missing clean marker: pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/sta.rpt |
| `utilization_report` | `present` | `manifest` | 1 | - |
| `congestion_report` | `present` | `manifest` | 1 | - |
| `density_fill_report` | `present` | `manifest` | 1 | - |
| `tool_versions` | `present` | `manifest` | 1 | - |

## Flow State

Every discovered numbered OpenLane step has `state_out.json`.

## Copied Files

### run_manifest
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/signoff-run.yaml` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/run_manifest/signoff-run.yaml`

### gds
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/gds/hello_chip_top.gds` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/gds/final/gds/hello_chip_top.gds`

### def
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/def/hello_chip_top.def` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/def/final/def/hello_chip_top.def`

### gate_netlist
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/verilog/gl/hello_chip_top.v` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/gate_netlist/final/verilog/gl/hello_chip_top.v`

### corner_manifest
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/signoff-corners.yaml` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/corner_manifest/reports/signoff/signoff-corners.yaml`

### sdc
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdc/hello_chip_top.sdc` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdc/final/sdc/hello_chip_top.sdc`

### spef
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/spef/hello_chip_top.max.spef` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/spef/final/spef/hello_chip_top.max.spef`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/spef/hello_chip_top.min.spef` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/spef/final/spef/hello_chip_top.min.spef`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/spef/hello_chip_top.nom.spef` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/spef/final/spef/hello_chip_top.nom.spef`

### sdf
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__max_ff_n40C_1v95.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__max_ff_n40C_1v95.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__max_ss_100C_1v60.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__max_ss_100C_1v60.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__max_tt_025C_1v80.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__max_tt_025C_1v80.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__min_ff_n40C_1v95.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__min_ff_n40C_1v95.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__min_ss_100C_1v60.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__min_ss_100C_1v60.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__min_tt_025C_1v80.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__min_tt_025C_1v80.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__nom_ff_n40C_1v95.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__nom_ff_n40C_1v95.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__nom_ss_100C_1v60.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__nom_ss_100C_1v60.sdf`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/final/sdf/hello_chip_top__nom_tt_025C_1v80.sdf` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sdf/final/sdf/hello_chip_top__nom_tt_025C_1v80.sdf`

### drc_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/drc_klayout.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/drc_report/reports/signoff/drc_klayout.rpt`
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/drc_magic.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/drc_report/reports/signoff/drc_magic.rpt`

### lvs_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/lvs.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/lvs_report/reports/signoff/lvs.rpt`

### antenna_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/antenna.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/antenna_report/reports/signoff/antenna.rpt`

### sta_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/sta.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/sta_report/reports/signoff/sta.rpt`

### utilization_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/utilization.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/utilization_report/reports/signoff/utilization.rpt`

### congestion_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/congestion.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/congestion_report/reports/signoff/congestion.rpt`

### density_fill_report
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/density_fill.rpt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/density_fill_report/reports/signoff/density_fill.rpt`

### tool_versions
- `pd/openlane/runs/RUN_2026-05-18_05-41-42/reports/signoff/tool_versions.txt` -> `build/pd-signoff-archives/RUN_2026-05-18_05-41-42/artifacts/tool_versions/reports/signoff/tool_versions.txt`
