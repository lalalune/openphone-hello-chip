# Hello demo FPGA target

The owned FPGA bring-up target is `hello_demo_fpga`. It is a non-fabrication target used to keep the chip-level interface runnable on a lab board before padframe and package data are final.

## Target scope

- Top-level RTL: `hello_chip_top`
- Primary board class: Lattice ECP5 ULX3S-style bring-up board
- Synthesis family: ECP5
- Intended flow: Yosys plus nextpnr-ecp5 when installed locally
- Clock input: single 25 MHz board oscillator adapted to `CLK_IN`
- Reset input: active-low pushbutton or supervisor adapted to `RST_N`
- Debug transport: low-speed GPIO bridge driving the demo MMIO pins
- GPIO outputs: eight LEDs or header pins
- IRQ outputs: routed to header pins or logic analyzer probes

The target contract is machine-readable in `board/fpga/hello_demo_fpga.yaml`. The constraints file in `board/fpga/constraints/hello_demo_ulx3s.lpf` is intentionally a skeleton until a specific ULX3S revision and connector assignment are selected.

## Gates

`make fpga-check` validates that the FPGA contract names the RTL top, clock, reset, debug, GPIO, and IRQ signals consistently with the current package and RTL contract. The check is a scaffold gate, not a bitstream build.

Bitstream generation must remain blocked until:

- Every `hello_chip_top` external signal has an assigned FPGA package pin.
- The assigned board revision is recorded.
- The clock constraint matches the physical oscillator.
- Reset polarity is verified on hardware.
- The debug bridge firmware or MCU host is identified.
