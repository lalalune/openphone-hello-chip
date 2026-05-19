# E1 AlphaChip Conversion Handoff

## Required E1 inputs

AlphaChip needs:

- Circuit Training protobuf netlist.
- Initial placement `.plc`.
- Floorplan dimensions and grid configuration.
- Macro dimensions, pins, orientations, fixed constraints, and spacing/halo
  policy.
- Routing resource assumptions and cost weights.

The E1 OpenLane flow currently provides RTL configs and constraints, but no
committed final LEF/DEF handoff. Generate the physical collateral through the
existing OpenLane/OpenROAD flow before converting.

## Preferred conversion path

1. Run E1 OpenLane to a point where synthesized netlist, technology LEFs,
   macro LEFs, and floorplan DEF are available.
2. Use `scripts/alphachip/convert_lefdef_to_pb.sh` to convert LEF/DEF to
   Circuit Training protobuf and initial PLC.
3. Run AlphaChip toy/smoke, then E1 training.
4. Convert the selected AlphaChip placement back to DEF.
5. Import that DEF via OpenLane `FP_DEF_TEMPLATE` for validation.

## Verified conversion command

The smoke DEF round-trip now works:

```sh
ALPHACHIP_OUT_DIR=/tmp/e1-alphachip/smoke_handoff \
  scripts/alphachip/convert_lefdef_to_pb.sh \
  --def pd/openlane/runs/RUN_2026-05-19_03-33-45/final/def/e1_pd_smoke_top.def
```

Outputs:

```text
/tmp/e1-alphachip/smoke_handoff/e1_pd_smoke_top.pb.txt
/tmp/e1-alphachip/smoke_handoff/e1_pd_smoke_top.init.plc
```

This uses the TILOS `gen_pb_or.tcl` OpenDB exporter under the installed
OpenLane Docker image. The older TILOS Python `LefDef2ProBufFormat` path needs
an OpenROAD build with `partition_design`; the installed OpenLane OpenROAD does
not expose that command, and the bundled TILOS OpenROAD binary did not run
cleanly on the local host/container libraries.

## Blockers to resolve

- E1 macro inventory is not yet clear. Current RTL is mostly soft logic and
  stubs; AlphaChip is most valuable when SRAM/NPU/cache/peripheral macros are
  real hard macros.
- OpenLane/OpenROAD tools are not on the host PATH. The repo can use Docker;
  `ghcr.io/efabless/openlane2:2.4.0.dev1` is installed and has completed the
  smoke flow.
- The smoke design has zero hard macros, so it is not a useful AlphaChip
  optimization target. Use it only as an OpenLane/signoff sanity check.
- For macro-less or mostly soft-logic E1 variants, use TILOS clustering/hMETIS
  to create soft macros, or introduce real hard SRAM/cache/NPU macros before
  expecting AlphaChip to improve placement.

## E1 candidate output location

Use generated paths under:

```text
/tmp/e1-alphachip/e1/
  netlist.pb.txt
  initial.plc
  candidates/
    candidate_001.plc
    candidate_001.def
  reports/
```
