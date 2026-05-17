# Hello demo KiCad placeholder notes

This directory is reserved for the KiCad project once the pinout contract is stable.

Fabrication blockers:

- Package is placeholder-only.
- Footprint is not derived from a package vendor drawing.
- Power sequencing and decoupling values are preliminary.
- No SI/PI analysis has been performed.
- No assembly house DFM review has been performed.

Bring-up intent:

1. Current-limit both rails.
2. Confirm `1.8 V` and `3.3 V` rails.
3. Confirm external clock.
4. Release reset.
5. Read ROM ID over debug bus.
6. Toggle GPIO LEDs.
7. Run NPU add smoke command.
8. Observe IRQ outputs.
