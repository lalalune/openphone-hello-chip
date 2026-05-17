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
