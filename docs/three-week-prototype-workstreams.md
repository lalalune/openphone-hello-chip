# Three-week prototype workstreams

Generated on 2026-05-16 from subsystem agent reviews and local validation.
Updated on 2026-05-17 after the critical gap review pass.

## Current executable baseline

- Passing locally: `make docs-check project-plan-check platform-contract-check`, `make rtl-check`, `make synth`, `make formal`, `make verilator`, `make cocotb`, `make cocotb-contract`, `make cocotb-cpu`, `make qemu-check`, `make pipeline-check`, and `python3 scripts/check_mvp_status.py --fail-on-fail`.
- Blocked locally: `make openroad` and `make openlane` because OpenROAD/OpenLane/Magic/Netgen are not installed or pulled.
- Tooling caveat: cocotb now runs from the repo `.venv` path through the Makefile wrapper. Release evidence still needs clean-checkout regeneration and archived tool/report checksums.
- Blocked by evidence, not local syntax: Renode executable smoke, software BSP external build logs, product/package/board fabrication evidence, real benchmarks, and PD signoff artifacts.

## Critical architecture boundary

The current hello chip is a debug-MMIO hardware ABI, not a bootable phone SoC. `hello_chip_top` exposes a package debug nibble bridge into `hello_soc_top`. The Linux-capable AXI-Lite scaffold is separate under `rtl/interconnect`, `rtl/memory`, and `rtl/interrupts`; the CPU subsystem is intentionally non-bootable.

Prototype success in three weeks should therefore be defined as one of two tracks:

1. A stronger hello-chip demonstrator: debug bridge drives DMA/NPU/display contract behavior, with RTL/formal/cocotb/synthesis/PD artifact evidence.
2. A Linux-capable scaffold prototype: integrate a real or simulated RV64 path, DRAM, interrupt/timer/UART, generated DTS, and boot smoke tests.

Treating QEMU/Renode success as proof of the hello-chip ABI is invalid until an emulator model exists for the hello hardware map.

## Workstream A: RTL and formal

Primary gaps:

- Detailed RTL/SoC gap inventory is maintained in `docs/project/rtl-soc-critical-gap-audit.md` and enforced as open machine-readable work orders by `verify/rtl_gap_work_order.yaml`.
- No real CPU, cache/MMU, memory controller, or shared-memory path in pad-level RTL.
- DMA has a prototype AXI-Lite memory master, but no production memory hierarchy, coherency policy, long-burst coverage, or throughput evidence.
- NPU is register-datapath only: no descriptors, queue, scratchpad, tensor layout, or backpressure.
- Display has a top-level SRAM-backed framebuffer read path verified by cocotb, but no production framebuffer client, panel PHY/DSI bridge, format conversion pipeline, or hardware-in-loop evidence.
- Formal is shallow BMC and misses AXI-Lite, DRAM, interrupt controller, display, reset, and CPU-contract wrappers.

Immediate work:

- Add randomized cocotb/reference-model coverage for all NPU opcodes, DMA edge cases, display timing, and AXI-Lite stalls.
- Add protocol assertions or an open AXI-Lite property set for interconnect, DRAM, and interrupt controller.
- Add coverage summaries for opcodes, MMIO regions, response codes, IRQs, and AXI timing permutations.
- Keep `make formal` fallback evidence labeled as fallback unless `REQUIRE_SBY=1` is set, and require `REQUIRE_DEEP_FORMAL=1` before treating top-level BMC as more than routine structural coverage.
- Decide whether week-one RTL work targets the hello debug-MMIO demonstrator or the Linux-capable scaffold; they are different prototypes.

## Workstream B: software, boot, OS, simulation

Primary gaps:

- Platform contract had drifted behind extended DMA/NPU RTL registers. This report run updated the JSON/header and checker to catch future undocumented readable RTL offsets.
- Linux drivers now consume the generated platform contract import header, and the platform-contract checker rejects stale generated/imported headers.
- DTS is not bootable: no CPU, memory, timer, interrupt-parent, UART, or complete RISC-V platform shape.
- `qemu-check` now builds/runs the qemu-virt software-reference firmware and archives `build/reports/qemu_smoke.log`; this is still not hello-chip hardware boot proof.
- `renode-check` remains a semantic scaffold plus explicit BLOCK until `renode` is installed and a transcript is archived.
- Buildroot/AOSP/OpenSBI/U-Boot paths are placeholders around external trees.

Immediate work:

- Generate DTS/include fragments from `sw/platform/hello_platform_contract.json`.
- Keep QEMU transcript evidence in `build/reports/qemu_smoke.log` and prevent qemu-virt success from being described as hello-chip hardware boot.
- Split software checks into scaffold checks versus real boot/image checks.
- Produce external Linux, Buildroot, and AOSP logs before allowing `make software-bsp-evidence-check` to pass.

## Workstream C: PD, package, board, SI/PI

Primary gaps:

- Padless PD only; no foundry IO cells, ESD clamps, corner pads, padframe-inclusive DRC/LVS, or package-approved bond diagram.
- No complete PD signoff run artifacts under the manifest.
- Signoff checker now names liberty/corners, SPEF/SDF, utilization/congestion, density/fill, tool-version, and waiver evidence as release artifacts, but no real run has produced them yet.
- Board/package are planning placeholders. No vendor-derived footprint, real KiCad project, rail current budget, PDN target impedance, decap plan, SI/PI report, or DFM review exists.
- FPGA LPF is a skeleton; no bitstream build target can be released until pins and IO standards are real.

Immediate work:

- Produce real OpenLane/OpenROAD signoff output for every artifact class named by `scripts/check_pd_signoff.py` and `pd/signoff/manifest.yaml`.
- Keep `docs/manufacturing/physical-closure-work-order.yaml` in sync with footprint checksum, current budget, SI/PI report, DFM review, and first-article checklist gates.
- Add an FPGA build target after pins are assigned: Yosys, nextpnr-ecp5, ecppack, and timing report parse.

## Workstream D: ISP, display, real-world verification

Primary gaps:

- No camera/ISP contract exists: no CSI/MIPI, sensor power/reset/I2C, calibration assets, tuning tables, image-quality tests, or board constraints.
- Display now has SRAM-backed framebuffer fetch and underflow accounting in the top-level demonstrator, but still lacks pixel formats beyond scaffold registers, panel init, DSI/PHY bridge, gamma/color, buffering, bandwidth checks, and real panel validation.
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
- Repo-local `.venv` is the current cocotb path. Release-grade reproducibility still needs clean-checkout regeneration and archived package/tool checksums.

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
