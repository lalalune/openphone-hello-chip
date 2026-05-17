# Hello demo pad ring assumptions

Evidence class: `non_release_placeholder`
Release use: `prohibited`

The current RTL does not instantiate foundry pad cells. This file is a planning contract only, not pad-ring release evidence. The pad ring contract is:

- Power pads: multiple `VDDIO`, `VSSIO`, `VDDCORE`, and `VSSCORE` pins.
- Clock pad: one low-skew digital clock input.
- Reset pad: one Schmitt-trigger active-low reset input with pull-up.
- Digital input pads: debug bus and test/JTAG inputs.
- Digital output pads: debug readback, ready, IRQ, GPIO.
- ESD: provided by selected foundry pad library.
- Corner pads: selected by the shuttle/package flow.

The current OpenLane block should be treated as a core/hard-macro candidate until real pads are selected.

## Release blockers

- Foundry IO, power, ground, corner, clamp, and ESD cells are not selected.
- Pad-ring floorplan, pad placement, and bond-pad geometry are not implemented.
- Padframe-inclusive DRC/LVS has not run.
- Bond diagram and package mapping are missing.

Do not use this file as fabrication, tapeout, or package release evidence.
