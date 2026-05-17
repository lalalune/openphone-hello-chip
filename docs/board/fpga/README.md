# Hello demo FPGA target

The owned FPGA bring-up target is `hello_demo_fpga`. It is a non-fabrication target used to keep the chip-level interface runnable on a lab board before padframe and package data are final.

The FPGA prototyping strategy for this program is **two-stage**. See
`docs/board/fpga/platform-selection.md` for the platform decision and the
resource-budget rationale.

- Stage 1 (now, hello-demo MMIO): **Lattice ECP5 on ULX3S 85F**, fully
  open-source toolchain (Yosys / nextpnr-ecp5 / ecppack / openFPGALoader).
- Stage 2 (M5+, Rocket + Gemmini): **Xilinx VCU118** on-prem or
  **FireSim on AWS F1** in the cloud. See `board/fpga/vcu118/README.md` and
  `docs/board/fpga/firesim-bringup.md`.

## Stage 1 target scope (this document)

- Top-level RTL: `hello_chip_top`
- Primary board class: Lattice ECP5 ULX3S 85F (revision F)
- Synthesis family: ECP5
- Intended flow: Yosys plus nextpnr-ecp5 with ecppack and openFPGALoader
- Clock input: single 25 MHz board oscillator adapted to `CLK_IN`
- Reset input: active-low pushbutton or supervisor adapted to `RST_N`
- Debug transport: low-speed GPIO bridge driving the demo MMIO pins
- GPIO outputs: eight LEDs or header pins
- IRQ outputs: routed to header pins or logic analyzer probes

The target contract is machine-readable in `board/fpga/hello_demo_fpga.yaml`.
Concrete pin assignments for ULX3S 85F rev F now live in
`board/fpga/constraints/hello_demo_ulx3s.lpf` (defensible defaults; see the
header of that file for the assumptions to revisit per board revision).

## Build flow (Stage 1)

- `board/fpga/Makefile` drives `synth`, `pnr`, `pack`, `prog`, `report`,
  `clean` against the OSS CAD Suite tools.
- `scripts/fpga/build_hello_demo.sh` is the end-to-end wrapper that runs
  synth -> pnr -> pack and archives logs and provenance under
  `build/fpga/hello_demo/archive/<utc-timestamp>/`.

Neither path is invoked by CI. Bitstream generation runs on the developer or
lab machine that has yosys, nextpnr-ecp5, and ecppack installed.

## Gates

`make fpga-check` validates that the FPGA contract names the RTL top, clock,
reset, debug, GPIO, and IRQ signals consistently with the current package
and RTL contract. The check is a scaffold gate, not a bitstream build.

Bitstream release for hello-demo remains blocked until:

- Every `hello_chip_top` external signal has an assigned FPGA package pin
  that matches the physical board on the bench.
- The assigned board revision is recorded in `hello_demo_fpga.yaml`.
- The clock constraint matches the physical oscillator.
- Reset polarity is verified on hardware.
- The debug bridge firmware or MCU host is identified.

## Related documents

- `docs/board/fpga/platform-selection.md` -- two-stage strategy and budgets.
- `board/fpga/vcu118/README.md` -- Stage 2 VCU118 plan for Rocket+Gemmini.
- `docs/board/fpga/firesim-bringup.md` -- Stage 2 AWS F1 runbook.
- `docs/rtl/open_rtl_prototype_path.md` -- RTL strategy this platform supports.
- `docs/project/board-package-pd-fpga-critical-gap-audit.md` -- audit.
