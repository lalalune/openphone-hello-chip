# Hello demo padframe plan

The first physical implementation target is a padless digital core. The standalone chip wrapper is specified by `package/hello-demo-pinout.yaml`.

Required before fabrication:

- Select open shuttle or foundry pad library.
- Instantiate IO, power, ground, and corner pads.
- Add tie-high/tie-low cells for fixed test straps.
- Add ESD-compliant power clamp strategy.
- Add bonding diagram and package mapping.
- Re-run LVS/DRC against the padframe-inclusive top.
