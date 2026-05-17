# Physical design signoff — hello chip

This document covers the full OpenLane 2 PD flow for `hello_chip_top` on SKY130A,
the prerequisite environment, how to launch a run, what outputs to expect, and the
pass criteria for each signoff check.

The machine-readable artifact gate lives in `pd/signoff/manifest.yaml`. The manifest
schema is `pd/signoff/run-manifest.schema.json`. Signoff checks are run with:

```sh
make pd-signoff-manifest-check   # fast structural check (no tool output needed)
make pd-signoff-check            # hard release gate
```

---

## Required signoff artifacts

A run passes when **one selected run directory** under `pd/openlane/runs/` contains
all of the following, non-empty:

| Artifact | Glob inside run directory |
|----------|--------------------------|
| Routed GDS | `final/gds/*.gds` |
| Final DEF | `final/def/*.def` |
| Gate netlist | `final/verilog/gl/*.v` |
| SDC (copy) | `final/sdc/*.sdc` |
| SPEF | `final/spef/*.spef` |
| SDF | `final/sdf/*.sdf` |
| DRC report | `final/drc/*.rpt` or `reports/signoff/*drc*.rpt` |
| LVS report | `final/lvs/*.rpt` or `reports/signoff/*lvs*.rpt` |
| Antenna report | `final/antenna/*.rpt` or `reports/signoff/*antenna*.rpt` |
| STA report (per corner) | `final/sta/*.rpt` or `reports/signoff/*sta*.rpt` |
| Utilization report | `reports/signoff/*util*.rpt` or `reports/final/*util*.rpt` |
| Congestion report | `reports/signoff/*congestion*.rpt` or `reports/routing/*congestion*.rpt` |
| Density/fill report | `reports/signoff/*density*.rpt` or `reports/signoff/*fill*.rpt` |
| Tool-version record | `tool_versions.txt` or `reports/signoff/tool_versions.txt` |
| Corner manifest | `signoff-corners.yaml` or `reports/signoff/*corner*.yaml` |
| Run manifest | `signoff-run.yaml` or `reports/signoff/signoff-run.yaml` |
| Waivers (if any report dirty) | `pd/signoff/waivers/*.yaml` |

Beyond PD release, standalone chip tapeout also requires SI/PI, PDN/current-budget,
and padframe/package evidence — see `pd/signoff/manifest.yaml` for the full gate
list.

---

## Prerequisites

### Software

| Tool | Install | Version used |
|------|---------|--------------|
| OpenLane 2 | `pip3 install openlane` | 2.4.0.dev1 (pinned in manifest) |
| Volare (PDK manager) | `pip3 install volare` | latest |
| SKY130A PDK | `volare enable --pdk sky130 latest` | sky130-2024.* |
| Docker (optional fallback) | docker.com | 24+ |

### Hardware

- 8-core / 16-thread CPU recommended (routing is highly parallel)
- 32 GB RAM minimum (global routing on a 2.5 mm die uses ~24 GB peak)
- 20 GB free disk (run directory including GDS, DEF, SPEF)

### Environment

```sh
export PDK_ROOT=$HOME/.volare   # default; set to your volare root
```

The `run.sh` script defaults `PDK_ROOT` to `$HOME/.volare` if the variable is unset.

---

## Running the flow

```sh
# Full SoC (hello_chip_top, 2500x2500 um die)
cd /path/to/npu_experiment
./pd/openlane/run.sh

# Small smoke design (hello_pd_smoke_top, 180x180 um die, ~2 min)
./pd/openlane/run.sh --smoke
```

Alternatively, from the `pd/openlane/` directory:

```sh
make pd          # full run
make pd-smoke    # smoke run (if target exists in Makefile)
make pd-check    # prerequisite check only
```

The flow runs the pinned Docker image automatically if the `openlane` CLI is not
found on `$PATH`.

### Expected runtime

| Design | Cores | Wall time |
|--------|-------|-----------|
| `hello_pd_smoke_top` (180 um) | 4 | ~2 min |
| `hello_chip_top` (2500 um) | 8 | 4–8 hours |

---

## Output artifacts

A completed run populates `pd/openlane/runs/RUN_<timestamp>/`:

```
final/
  gds/hello_chip_top.gds        # GDSII for tape-out / DRC
  def/hello_chip_top.def        # placed-and-routed DEF
  verilog/gl/hello_chip_top.v   # gate-level netlist
  sdc/hello_chip_top.sdc        # timing constraints copy
  spef/                         # extracted parasitics (per corner)
  sdf/                          # back-annotated timing delays
reports/
  signoff/                      # DRC, LVS, antenna, STA, utilisation
  routing/                      # congestion, wire-length
  power/                        # post-route power estimates
```

`run.sh` also mirrors signoff reports to `build/pd/signoff/` for fast local review.

---

## Pass criteria per signoff check

### DRC (Magic + KLayout)

- **Pass:** 0 violations in both Magic and KLayout reports.
- **Waiver path:** `pd/signoff/waivers/`. Each waiver must name the violated rule,
  measured value, limit, affected net or shape, risk, owner, and expiry condition.
- Config knobs: `QUIT_ON_MAGIC_DRC: false` (MVP — violations are logged, not fatal).

### LVS (Netgen + Magic)

- **Pass:** "Circuits match" or "LVS clean" in the Netgen report.
- **Fail patterns:** "netlists do not match", "mismatch".
- Config knobs: `QUIT_ON_LVS_ERROR: false` (MVP).

### Antenna (OpenROAD)

- **Pass:** 0 antenna violations after diode insertion (`RUN_HEURISTIC_DIODE_INSERTION: true`).

### STA (OpenROAD OpenSTA, post-PnR with SPEF)

Corners analysed:

| Corner label | Library corner | Voltage | Temp | Analysis |
|---|---|---|---|---|
| `nom_tt_025C_1v80` | TT | 1.80 V | 25 °C | nominal |
| `nom_ff_n40C_1v95` | FF | 1.95 V | −40 °C | best-case hold |
| `nom_ss_100C_1v60` | SS | 1.60 V | 100 °C | worst-case setup |
| `max_ss_100C_1v60` | SS | 1.60 V | 100 °C | setup signoff |
| `min_ff_n40C_1v95` | FF | 1.95 V | −40 °C | hold signoff |

- **Pass:** WNS ≥ 0 ns for setup across all corners; WNS ≥ 0 ns for hold.
- Config knobs: `QUIT_ON_TIMING_VIOLATIONS: false` (MVP — violations are logged).
- Critical path expected through the NPU GEMM datapath (multicycle path set to 2
  cycles in the SDC).

### Utilisation and congestion

- **Utilisation:** target 35 % core utilisation (`FP_CORE_UTIL: 35`).
- **Congestion:** global routing overflow = 0 (`GRT_OVERFLOW_ITERS: 50` budget).

---

## Viewing results

```sh
# GDS in KLayout
klayout pd/openlane/runs/RUN_<tag>/final/gds/hello_chip_top.gds

# Interactive OpenROAD GUI (after routing)
openroad -gui pd/openlane/runs/RUN_<tag>/final/def/hello_chip_top.def

# STA reports
less pd/openlane/runs/RUN_<tag>/55-openroad-stapostpnr/max_ss_100C_1v60/sta.log
```

---

## Release gate status

The three product release gates are tracked in `pd/signoff/manifest.yaml`:

| Gate | Status | Unblock requires |
|------|--------|-----------------|
| `pd_release` | **blocked** | Complete selected run with all artifact classes |
| `tapeout_release` | **blocked** | SI/PI, PDN/current-budget, padframe/package evidence |
| `board_fabrication_release` | **blocked** | Package drawing, footprint, SI, PI, DFM, first-article limits |

Run `python3 scripts/check_pd_signoff.py --manifest-only` to validate gate
consistency without requiring tool output.
