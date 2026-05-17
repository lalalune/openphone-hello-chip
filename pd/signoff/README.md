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
- SI/PI evidence for package models, board-level signal integrity, and power integrity.
- PDN/current-budget evidence for post-route power, IR-drop/EM, decoupling, and board current limits.
- Padframe/package evidence for foundry IO/ESD/corner cells, package drawing, bond diagram, and footprint release.

The current `hello_soc_top` can be hardened as a padless macro. A standalone fabricated chip also requires the padframe plan in `pd/padframe/hello_demo_padframe.md`.

The machine-readable artifact gate is `pd/signoff/manifest.yaml`.

Run:

```sh
make pd-signoff-manifest-check
make pd-signoff-check
```

The manifest check validates required artifact classes, run-scoped globs, explicit blocked gates, and the SI/PI, PDN/current-budget, and padframe/package readiness sections without requiring tool output, so it is safe for fast product checks. The full signoff check is a hard release gate: one OpenLane/OpenROAD run directory must contain nonempty final GDS, DEF, gate netlist, SDC, DRC, LVS, antenna, and STA artifacts, signoff reports must include clean markers while avoiding failure patterns, and release gates must no longer be blocked.
