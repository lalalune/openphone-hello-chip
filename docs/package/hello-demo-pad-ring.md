# Hello demo pad ring assumptions

The current RTL does not instantiate foundry pad cells. The pad ring contract is:

- Power pads: multiple `VDDIO`, `VSSIO`, `VDDCORE`, and `VSSCORE` pins.
- Clock pad: one low-skew digital clock input.
- Reset pad: one Schmitt-trigger active-low reset input with pull-up.
- Digital input pads: debug bus and test/JTAG inputs.
- Digital output pads: debug readback, ready, IRQ, GPIO.
- ESD: provided by selected foundry pad library.
- Corner pads: selected by the shuttle/package flow.

The current OpenLane block should be treated as a core/hard-macro candidate until real pads are selected.
