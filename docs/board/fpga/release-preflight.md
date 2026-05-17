# FPGA release preflight

`hello_demo_fpga` is blocked from bitstream release until the repository contains reproducible board, pin, timing, bitstream, and toolchain evidence. The scaffold contract is checked by `make fpga-check`; release evidence is checked by `make fpga-release-check`.

The release check is intentionally stricter than the scaffold check. It requires:

- `board/fpga/hello_demo_fpga.yaml` to be `status: release_ready`.
- `board.exact_revision`, `board.exact_revision_evidence`, `board.ecp5_device`, and `board.ecp5_package` to name a real board and FPGA part/package.
- `constraints.final_lpf` to point to a final LPF, not the skeleton LPF.
- One non-comment `LOCATE COMP` assignment for every required physical `hello_chip_top` signal.
- A clock frequency constraint for `CLK_IN` matching the manifest frequency.
- Local `nextpnr-ecp5` and `ecppack` tools to be available when claiming timing or bitstream evidence.
- Archived timing report, bitstream file, SHA-256 digest, and tool versions.

Do not guess LOCATE pins from a board class. Use the exact board revision schematic or vendor pin table, then archive the source in the release manifest before enabling bitstream release.
