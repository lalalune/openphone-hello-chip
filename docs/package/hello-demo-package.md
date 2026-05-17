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
