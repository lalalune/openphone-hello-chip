# Three-week prototype workstreams

Generated on 2026-05-16 from subsystem agent reviews and local validation.

## Current executable baseline

- Passing locally: `make docs-check platform-contract-check product-check`, `make rtl-check`, `make synth`, `make formal`, `make verilator`, `make cocotb`, and `make cocotb-contract`.
- Blocked locally: `make openroad` and `make openlane` because OpenROAD/OpenLane/Magic/Netgen are not installed or pulled.
- Tooling caveat: cocotb now runs from the user Python site. A repo-local virtual environment is still needed so NumPy/pytest/cocotb do not perturb unrelated Python packages.

## Critical architecture boundary

The current hello chip is a debug-MMIO hardware ABI, not a bootable phone SoC. `hello_chip_top` exposes a package debug nibble bridge into `hello_soc_top`. The Linux-capable AXI-Lite scaffold is separate under `rtl/interconnect`, `rtl/memory`, and `rtl/interrupts`; the CPU subsystem is intentionally non-bootable.

Prototype success in three weeks should therefore be defined as one of two tracks:

1. A stronger hello-chip demonstrator: debug bridge drives DMA/NPU/display contract behavior, with RTL/formal/cocotb/synthesis/PD artifact evidence.
2. A Linux-capable scaffold prototype: integrate a real or simulated RV64 path, DRAM, interrupt/timer/UART, generated DTS, and boot smoke tests.

Treating QEMU/Renode success as proof of the hello-chip ABI is invalid until an emulator model exists for the hello hardware map.

## Workstream A: RTL and formal

Primary gaps:

- No real CPU, cache/MMU, memory controller, or shared-memory path in pad-level RTL.
- DMA has no memory master read/write interface.
- NPU is register-datapath only: no descriptors, queue, scratchpad, tensor layout, or backpressure.
- Display generates a pattern rather than fetching framebuffer memory.
- Formal is shallow BMC and misses AXI-Lite, DRAM, interrupt controller, display, reset, and CPU-contract wrappers.

Immediate work:

- Add randomized cocotb/reference-model coverage for all NPU opcodes, DMA edge cases, display timing, and AXI-Lite stalls.
- Add protocol assertions or an open AXI-Lite property set for interconnect, DRAM, and interrupt controller.
- Add coverage summaries for opcodes, MMIO regions, response codes, IRQs, and AXI timing permutations.
- Decide whether week-one RTL work targets the hello debug-MMIO demonstrator or the Linux-capable scaffold; they are different prototypes.

## Workstream B: software, boot, OS, simulation

Primary gaps:

- Platform contract had drifted behind extended DMA/NPU RTL registers. This report run updated the JSON/header and checker to catch future undocumented readable RTL offsets.
- Linux drivers still hardcode constants instead of consuming generated contract headers.
- DTS is not bootable: no CPU, memory, timer, interrupt-parent, UART, or complete RISC-V platform shape.
- `qemu-check` and `renode-check` are scaffold echoes, not boot validation.
- Buildroot/AOSP/OpenSBI/U-Boot paths are placeholders around external trees.

Immediate work:

- Generate DTS/include fragments from `sw/platform/hello_platform_contract.json`.
- Build `sw/bootrom/hello_qemu_firmware.S` into an ELF and make `qemu-check` assert serial output under timeout.
- Split software checks into scaffold checks versus real boot/image checks.
- Replace driver constants with generated headers or generated local include files.

## Workstream C: PD, package, board, SI/PI

Primary gaps:

- Padless PD only; no foundry IO cells, ESD clamps, corner pads, padframe-inclusive DRC/LVS, or package-approved bond diagram.
- No complete PD signoff run artifacts under the manifest.
- Signoff checker now names liberty/corners, SPEF/SDF, utilization/congestion, density/fill, tool-version, and waiver evidence as release artifacts, but no real run has produced them yet.
- Board/package are planning placeholders. No vendor-derived footprint, real KiCad project, rail current budget, PDN target impedance, decap plan, SI/PI report, or DFM review exists.
- FPGA LPF is a skeleton; no bitstream build target can be released until pins and IO standards are real.

Immediate work:

- Produce real OpenLane/OpenROAD signoff output for every artifact class named by `scripts/check_pd_signoff.py` and `pd/signoff/manifest.yaml`.
- Add board/package gates for footprint checksum, current budget, SI/PI report, DFM review, and first-article checklist.
- Add an FPGA build target after pins are assigned: Yosys, nextpnr-ecp5, ecppack, and timing report parse.

## Workstream D: ISP, display, real-world verification

Primary gaps:

- No camera/ISP contract exists: no CSI/MIPI, sensor power/reset/I2C, calibration assets, tuning tables, image-quality tests, or board constraints.
- Display lacks framebuffer fetch, pixel formats beyond scaffold registers, panel init, DSI/PHY bridge, gamma/color, underflow handling, and real panel validation.
- Real-world verification is currently artifact/contract oriented, not hardware-in-loop.

Immediate work:

- Add an explicit camera/ISP not-implemented contract if camera remains in product scope.
- Add display validation around scanout DMA, format conversion, vsync semantics, underflow, mode programming, and software driver contract tests.
- Define bring-up evidence: FPGA board, logic analyzer traces, power measurements, serial logs, and signed-off manufacturing artifacts.

## Workstream E: toolchain and upstreams

Primary gaps:

- Docker apt packages and Nix `nixos-unstable` float; no `flake.lock` exists.
- Bootstrap scripts clone moving OpenLane2/Chipyard branches.
- OpenLane/OpenROAD/Magic/Netgen/Renode/KiCad are missing locally.
- Boolector is end-of-maintenance; Bitwuzla should be evaluated for future formal work.
- A repo-local `.venv` is not yet guaranteed; cocotb evidence from user-site Python is not release-grade.

Upstream review targets:

- OpenLane2 tags and PRs: https://github.com/chipfoundry/openlane2/tags
- Chipyard releases: https://github.com/ucb-bar/chipyard/releases
- OSS CAD Suite/Yosys/SBY/nextpnr/OpenROAD releases: https://github.com/YosysHQ/oss-cad-suite-build/releases, https://github.com/YosysHQ/yosys/releases, https://github.com/YosysHQ/nextpnr/releases, https://github.com/The-OpenROAD-Project/OpenROAD/tags
- cocotb/Python dependency upgrade path: https://github.com/cocotb/cocotb/releases
- Renode/KiCad only when those paths become release gates.

Fork policy:

- Do not vendor Chipyard, OpenLane/OpenROAD, PDKs, AOSP, or OSS CAD Suite.
- Pin reproducible refs, image digests, and tarball checksums.
- Fork only for unavoidable local patches that block a release; keep fork branches thin and upstream-rebaseable.

Validation commands:

- `scripts/check_tools.sh` inventories fast, host, and heavy tools without installing anything.
- `scripts/check_tools.sh --strict` fails when required fast-path Python packages are missing.
- `scripts/tool_versions.sh` records command paths, versions, Python package versions, and hashes for the toolchain control files.

Blockers to close before release-grade reproducibility:

- create `.venv` from `requirements.txt` and use it for cocotb/docs checks,
- commit or archive a Python lock/constraints file,
- pin Docker by digest or archive an apt package manifest,
- commit `flake.lock` if Nix is a supported path,
- replace default-branch OpenLane2/Chipyard clones with selected tags/SHAs,
- record image digests/checksums for OpenLane, OSS CAD Suite, PDK archives, and any forked tool refs.

## Three-week cadence

Week 1:

- Close verification/tooling drift: isolated Python env, source manifest, stronger platform-contract check, qemu-stub build, cocotb/formal coverage expansion.
- Run `scripts/check_tools.sh` and `scripts/tool_versions.sh`; attach `build/reports/tool_versions.txt` to evidence notes.
- Pick prototype track: debug-MMIO demonstrator or Linux-capable scaffold.

Week 2:

- Implement the chosen track end to end.
- For debug-MMIO: connect stronger DMA/NPU/display behavior and verify from runtime/tests.
- For Linux scaffold: add bootable CPU/timer/UART/memory contract and build a QEMU/Renode boot smoke.

Week 3:

- Harden evidence: full CI target, PD/signoff manifest enforcement, FPGA/board/package gates, release archive, and residual risk report.
- Keep non-passing gates named as blocked gates, not passing scaffold checks.
