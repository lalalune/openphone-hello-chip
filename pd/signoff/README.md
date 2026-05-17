# Physical signoff gates

The demo chip cannot be called tapeout-ready until the selected PDK flow archives:

- Routed GDS/OASIS.
- Final DEF.
- Gate-level netlist.
- Liberty/corner list.
- SDC.
- SPEF/SDF when available.
- DRC report.
- LVS report.
- Antenna report.
- STA WNS/TNS per corner.
- Utilization/congestion report.
- Density/fill report.
- Waiver file for every non-clean check.

The current `hello_soc_top` can be hardened as a padless macro. A standalone fabricated chip also requires the padframe plan in `pd/padframe/hello_demo_padframe.md`.

The machine-readable artifact gate is `pd/signoff/manifest.yaml`.

Run:

```sh
make pd-signoff-manifest-check
make pd-signoff-check
```

The manifest check validates required artifact classes and run-scoped globs without requiring tool output, so it is safe for fast product checks. The full signoff check is a hard release gate: one OpenLane/OpenROAD run directory must contain nonempty final GDS, DEF, gate netlist, SDC, DRC, LVS, antenna, and STA artifacts, and signoff reports must include clean markers while avoiding failure patterns.
