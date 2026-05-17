# Workstream Gap Review

Generated on 2026-05-16 from the project backlog, scaffold audits, and local
status notes. This is a gap inventory, not a completion report. A workstream may
have useful scaffolding and still be blocked from any product, silicon, Android,
or performance claim.

## Status terms

| Term | Meaning | Allowed claim |
|---|---|---|
| Complete gap | No release-grade implementation evidence exists in the repo yet. | Planning only. |
| Stub | Named code or metadata exists only to hold an interface, contract, or build slot. | Interface shape only. |
| Scaffold | A repo-local check or artifact exists, but it is not the real external build, boot, signoff, or hardware path. | Preflight only. |
| LARP | Text, scripts, or manifests could be mistaken for a working subsystem but do not execute the claimed subsystem. | No implementation claim. |
| Untested | Implementation-like code exists, but the relevant gate lacks coverage, transcripts, hardware logs, or external-tool output. | Experimental only. |
| Blocked | The next validation step requires a missing tool, selected ref, external checkout, board, package, or artifact. | Blocker must be named. |
| Done | Required artifacts exist, local and external gates pass, and release evidence records exact versions. | Bounded claim only. |

## Global claim gates

No workstream can move to Done unless all applicable gates below are satisfied.

| Gate | Completion criteria | Fails when |
|---|---|---|
| Evidence gate | Command transcript, report, log, or generated artifact is checked in or archived with a versioned path. | A passing statement has no artifact path. |
| Tool gate | Required tools, images, PDKs, external trees, and package versions are pinned by digest, lockfile, tag, SHA, or checksum. | A default branch, floating apt package set, or unrecorded local install is used as release evidence. |
| Boundary gate | The artifact says whether it proves hello-chip debug MMIO, Linux-capable scaffold behavior, qemu-virt software behavior, FPGA behavior, board behavior, or phone behavior. | QEMU, Renode, docs-only, or scaffold checks are described as hello-chip hardware proof. |
| Test gate | Unit, formal, integration, or hardware tests cover the claimed behavior and record pass/fail status. | The workstream only has syntax, schema, or existence checks. |
| Risk gate | Known exclusions and residual blockers are present in `docs/risks/risk-register.md`. | A known non-goal is omitted or softened. |
| Release gate | `make mvp-status` reports PASS, BLOCK, or FAIL with evidence and the next command. | Status is aspirational or missing a next command. |

## Workstream A: Program Controls And Release Claims

Owned backlog artifacts: `docs/project/**`, `docs/risks/**`,
`docs/three-week-prototype-workstreams.md`, `scripts/check_project_plan.py`.

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Stub/scaffold | `scripts/check_project_plan.py` validates required plan artifacts and selected table schemas, but it is not a full release-readiness checker. | Checker requires this gap review, risk evidence rows, workstream status categories, and claim-boundary language. | `make project-plan-check` |
| LARP risk | A green project-plan check can be mistaken for implementation progress. | Status docs must call out scaffold-only gates and point to subsystem-owned executable gates for real proof. | `make mvp-status` |
| Untested | Release archive inclusion is described, but not every new project-plan artifact is guaranteed in archive manifests. | Archive scripts/manifests include the gap review and risk register; archive smoke proves presence. | `make archive-release` |
| Blocked | Concurrent workers own many implementation paths, so this review cannot certify their work without their gates. | Every referenced subsystem gate is named as PASS, BLOCK, FAIL, or not owned. | Operating-loop review |

Done means project status can be reproduced from docs and scripts without
claiming unverified subsystem completion.

## Workstream B: SOTA References And Benchmark Boundaries

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Scaffold | SOTA and benchmark docs define claim levels and benchmark families. | Source URLs, benchmark schema, and comparison rules are all present and checked. | `make project-plan-check` |
| Untested | Benchmark report schema exists, but benchmark results can still be dry-run or placeholder-model blocked. | Real benchmark runs record platform, workload, clocks, memory, thermal, power, artifacts, and unsupported/fallback counts. | `make benchmarks` |
| Complete gap | No release-grade phone-level comparison exists for Android, NPU, GPU, sustained power, or thermal behavior. | L6 phone reports include CTS/VTS state, external power data, sustained loops, and no simulator wall-clock comparisons. | Benchmark review |
| LARP risk | Simulator output could be compared against commercial phone scores. | Schema and review gates reject simulator wall-clock comparisons. | `scripts/check_project_plan.py` |

Done means benchmark artifacts support only their declared L0-L6 claim level.

## Workstream C: RTL, Formal, And Verification

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Stub/scaffold | `hello_cpu_subsystem_stub` still names the boundary, while the Linux-capable AXI-Lite scaffold remains separate from pad-level hello chip. | Chosen prototype track is explicit: debug-MMIO demonstrator or Linux-capable scaffold, with integration evidence for that track. | `make rtl-check` plus track gate |
| Untested | Formal coverage is shallow for AXI-Lite, DRAM, interrupt controller, display, reset, and CPU-contract wrappers. | Protocol assertions or property sets cover those interfaces, with coverage reports archived. | `make formal` / deep formal gate |
| Untested | NPU, DMA, display, IRQ, and AXI timing behavior need randomized and reference-model coverage. | Coverage summaries name opcodes, MMIO regions, response codes, IRQs, stalls, and reset cases. | `make cocotb` / `make cocotb-contract` |
| Complete gap | No release-grade CPU/cache/MMU/DRAM-controller path is wired into the pad-level phone-style SoC. | Bootable CPU, memory, timer, interrupt, UART, generated DTS, and boot smoke exist for the Linux-capable track. | Linux scaffold boot gate |
| LARP risk | `make synth`, structural RTL checks, or scaffold wrappers may be treated as tapeout readiness. | Tapeout docs require signoff, PD, verification, and manufacturing gates before any silicon claim. | `make pipeline-check` |

Done means the selected RTL prototype has executable evidence at the claimed
boundary, not merely source files.

## Workstream D: Software, Boot, OS, QEMU, And Renode

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Scaffold | QEMU and Renode target qemu-virt software reference behavior, not the hello-chip hardware ABI. | Docs, scripts, and status output keep qemu-virt proof separate from hello-chip proof. | `make qemu-check renode-check` |
| Stub/scaffold | Buildroot, Linux, OpenSBI, U-Boot, and AOSP paths are repo-local scaffolds around external trees. | Import scripts and external build transcripts prove the real tree builds. | BSP build gates |
| Untested | Linux drivers and DTS paths need generated contract consumption and runtime smoke against real or emulated device nodes. | DTS/include fragments are generated from `sw/platform/hello_platform_contract.json`; MMIO smoke asserts device behavior. | `make software-bsp-check` plus boot smoke |
| Complete gap | No checked-in boot transcript proves Android or Linux boot on hello hardware. | Serial logs, kernel config, rootfs/image manifests, and command transcript are archived. | Boot evidence gate |
| LARP risk | Echo scripts or missing-tool status can look like boot validation. | Scaffold checks report BLOCK when QEMU/Renode/external trees are missing. | `make mvp-status` |

Done means boot claims are tied to a real target, a transcript, and reproducible
software inputs.

## Workstream E: Android BSP And Compatibility

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Stub/scaffold | Device tree, VINTF, init, SELinux, and HAL entries describe an external AOSP target. | External AOSP checkout builds vendor artifacts from the scaffold with a recorded command transcript. | `make aosp-bsp-check` plus AOSP build |
| Untested | HAL/device nodes are not compatibility evidence. | CTS/VTS subsets, SELinux denial logs, service liveness, and boot artifacts are recorded separately. | Android compatibility gate |
| Complete gap | No phone UI, Treble compliance, graphics stack, camera HAL3, modem integration, GMS, Widevine, or carrier certification exists. | Explicit exclusions remain until each domain has its own owner, tests, and evidence. | Risk gate |
| LARP risk | AOSP boot could be described as Android compatibility. | Docs and schema separate boot success from CTS/VTS compatibility. | `scripts/check_project_plan.py` |

Done means Android evidence states exactly whether it proves scaffold build,
boot, HAL liveness, or compatibility.

## Workstream F: PD, Package, Board, FPGA, SI/PI

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Stub/scaffold | Padframe, package, FPGA, and board files are planning contracts. | Exact board revision, package/vendor drawing, pin assignments, constraints, and release blockers are recorded. | `make product-check fpga-check` |
| Complete gap | No foundry IO ring, ESD, corner pads, package-approved bond diagram, vendor footprint, real KiCad project, SI/PI report, PDN target, or DFM review exists. | Vendor/package artifacts and board reviews are archived with checksums and reviewer status. | Board/package gate |
| Untested | OpenROAD/OpenLane signoff artifacts are incomplete or blocked when heavy tools are unavailable. | Real OpenLane/OpenROAD run outputs, manifests, corners, DRC/LVS, timing, area, power, SPEF/SDF, and waiver metadata are checked. | `make pd-signoff-check` |
| Blocked | Bitstream release is blocked while FPGA pins and board revision are unassigned. | Yosys, nextpnr-ecp5, ecppack, and timing report parse run against assigned pins. | FPGA bitstream gate |
| LARP risk | Placeholder package or LPF files could be used for fabrication or hardware claims. | Release checks reject fabrication/bitstream claims until all blockers close. | Product release gate |

Done means hardware artifacts can be built, reviewed, and reproduced for the
specific physical target being claimed.

## Workstream G: Product Interfaces, Display, Camera, WiFi, Sensors

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Stub/scaffold | WiFi/Bluetooth is product-scaffold only and not bonded into hello chip. | SDIO host, Bluetooth transport, firmware loading, regulatory path, DTS, and driver tests exist or remain excluded. | WiFi interface gate |
| Complete gap | Camera/ISP has no CSI/MIPI, sensor power/reset/I2C, tuning, calibration, image-quality, or HAL3 evidence. | A camera non-implementation contract is added, or a real camera workstream defines sensor, board, drivers, HAL, and IQ gates. | Camera scope gate |
| Untested | Display has scaffold registers and pattern behavior but lacks release-grade scanout validation. | Framebuffer fetch, pixel formats, vsync, underflow, panel init, DSI/PHY bridge, color/gamma, and driver tests pass. | Display validation gate |
| Complete gap | Sensor hub, modem, power management, security, and production peripheral policies are not implemented. | Each enters scope only with architecture contract, owner, tests, and release blockers. | Risk gate |
| LARP risk | Product interface YAML can look like implemented peripheral support. | Status fields stay scaffold/excluded until hardware and driver evidence exists. | Product check |

Done means an interface has hardware, software, and validation evidence, or is
explicitly excluded from the release claim.

## Workstream H: Toolchain, Reproducibility, And Upstreams

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Blocked | OpenLane/OpenROAD/Magic/Netgen/Renode/KiCad may be missing locally. | Missing tools are named with install/runtime requirements and mapped to blocked gates. | `scripts/check_tools.sh` |
| Stub/scaffold | Bootstrap scripts still depend on external tool and upstream setup behavior. | OpenLane2, Chipyard, OSS CAD Suite, PDK, Docker image, and Python package refs are pinned. | Toolchain release gate |
| Untested | Cocotb evidence from user-site Python is not release-grade. | Repo-local `.venv` or containerized Python environment is used and versions are archived. | `scripts/tool_versions.sh` |
| Complete gap | No complete release-grade reproducibility bundle exists until lockfiles/digests/checksums cover all required inputs. | Archive contains tool versions, source refs, image digests, generated reports, and blocker list. | `make archive-release` |
| LARP risk | Floating inputs can make a later run look like the same evidence. | Release docs reject floating defaults as evidence. | Project-plan and release review |

Done means a new engineer can reproduce the same claimed gates without relying
on hidden local state.

## Workstream I: Risk, Legal, Certification, And Non-Goals

| Gap class | Inventory | Completion criteria | Gate |
|---|---|---|---|
| Scaffold | Risk register covers major phone SoC scope exclusions and operational gates. | Every active non-goal maps to trigger, failure mode, mitigation, and versioned evidence path. | `make project-plan-check` |
| Complete gap | No carrier, GMS, Widevine L1, HDCP, modem, advanced-node, LPDDR PHY, production ISP, or copied-pinout path exists. | These remain non-goals or become separate programs with legal/certification owners. | Risk review |
| Untested | Risk severity and likelihood are manually maintained. | Release review compares risk rows against current workstream blockers and claim text. | Operating-loop review |
| LARP risk | Architecture budgets could be mistaken for product promises. | Risk triggers block flagship parity, drop-in compatibility, and production phone claims without evidence. | Risk gate |

Done means risk language is stricter than the most optimistic implementation
claim in the repo.

## Three-week gate schedule

| Week | Required decision or evidence | Exit gate |
|---|---|---|
| Week 1 | Choose debug-MMIO demonstrator or Linux-capable scaffold as the primary prototype track; create repo-local Python/tool evidence; split scaffold checks from real boot checks. | `make mvp-status` reports no unlabeled scaffold pass. |
| Week 2 | Implement the chosen track end to end and close generated contract drift for software, runtime tests, and verification coverage. | Track-specific RTL/software gate passes or reports a named BLOCK. |
| Week 3 | Harden release evidence, PD/signoff manifests, board/package gates, and residual risk review. | Archive contains evidence and blockers without invented completion claims. |

## Review checklist

- Each workstream has at least one executable or explicit blocked gate.
- Every stub, scaffold, placeholder, to-do marker, and not-implemented area is
  either owned by a future workstream or kept out of release claims.
- QEMU/Renode, docs-only, and metadata checks are never used as hardware proof.
- Android boot, Android compatibility, and complete phone behavior are tracked
  as separate claim levels.
- A missing tool is a BLOCK, not a PASS.
- Done requires evidence, pinned inputs, tests, and a risk-register boundary.
