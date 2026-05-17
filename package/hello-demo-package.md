# Hello demo package contract

The demo product target is a placeholder QFN64-style package for planning, review, and PCB bring-up flow validation.

This is not a foundry-approved package. It exists to make the top-level chip interface explicit while the project uses open PDK digital flows.

## Package assumptions

- 64 pins.
- `3.3 V` IO domain.
- `1.8 V` core domain.
- External clock input.
- Active-low reset input.
- Parallel debug/MMIO demo interface for board smoke tests.
- GPIO LED outputs.
- IRQ test-point outputs.
- JTAG pins reserved for future scan/debug.

Before fabrication, this document must be replaced by the actual shuttle/package/bonding document.

## Templates and bonding map

- `docs/package/bonding-diagram-template.md` defines the required vendor deliverables and the CSV column contract.
- `package/bonding/hello_demo_bonding.csv` is the canonical machine-readable die-pad <-> package-pin <-> board-net map (pre-filled from `package/hello-demo-pinout.yaml`).
- `docs/pd/pad-cell-selection-criteria.md` lists the pad/ESD requirements every candidate PDK must satisfy.
- `docs/manufacturing/release-evidence-template.md` describes the parent release manifest that ties together package vendor drawing, bonding diagram, IBIS, and board SI/PI/PDN reports.

Run `python3 scripts/check_pad_consistency.py` to cross-probe this pinout against the bonding CSV and the RTL top-level ports.
