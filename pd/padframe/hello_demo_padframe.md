# Hello demo padframe plan

The first physical implementation target is a padless digital core. The standalone chip wrapper is specified by `package/hello-demo-pinout.yaml`.

The machine-readable padframe contract is `pd/padframe/hello_demo_padframe.yaml`. Run `make padframe-check` before changing the package pinout, top-level ports, or OpenLane pin-order file.

Required before fabrication:

- Select open shuttle or foundry pad library.
- Instantiate IO, power, ground, and corner pads.
- Add tie-high/tie-low cells for fixed test straps.
- Add ESD-compliant power clamp strategy.
- Add bonding diagram and package mapping.
- Re-run LVS/DRC against the padframe-inclusive top.

The contract check requires contiguous package pins, legal pad classes, sufficient power/ground pad counts, matching top-level RTL ports, and `pd/pin_order.cfg` coverage for every `hello_chip_top` port.

## Templates and cross-probe

The foundry-agnostic artifacts required before a PDK can be selected and bonded live alongside this plan:

- `docs/pd/pad-cell-selection-criteria.md` - required pad classes, drive/slew options, ESD targets, and the PDK decision matrix.
- `docs/package/bonding-diagram-template.md` and the canonical bonding map at `package/bonding/hello_demo_bonding.csv`.
- `docs/pd/signoff-evidence-template.md` - artifact checklist for `build/pd/signoff/<RUN_ID>/`.
- `docs/manufacturing/release-evidence-template.md` - parent release manifest with PDK, package, bonding, IBIS, board SI/PI/PDN, and first-article evidence.

Run `python3 scripts/check_pad_consistency.py` to cross-probe the RTL top, the bonding CSV, the pinout YAML, and (if present) the KiCad netlist. The report is written to `build/reports/pad_consistency.json`.
