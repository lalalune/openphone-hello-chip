# Headless CLI Audit

Every tool used by this project must have a command-line path. GUI tools are
allowed only when their CLI/export path is the repo-controlled interface.

| Tool | Repo entrypoint | Headless status | Current blocker |
|---|---|---|---|
| Docker | `docker build`, `docker run ... make ci-fast` | Works headless | Docker daemon required. |
| Nix | `nix develop` | Works headless | `flake.lock` is not pinned yet. |
| Python deps | `make venv`, `requirements.txt` | Works headless | Host must use `.venv` or Docker. |
| Verilator | `make rtl-check`, `make verilator`, cocotb backend | Works headless | None in Docker path. |
| Yosys | `make synth`, formal fallback | Works headless | Full proof still needs SymbiYosys. |
| SymbiYosys | `make ci-strict` with `REQUIRE_SBY=1` | CLI-only | Not installed in fast Docker image. |
| cocotb | `make cocotb`, `make cocotb-contract`, `make cocotb-cpu` | Works headless | Requires Python env plus Verilator/Icarus. |
| QEMU | `make qemu-check`, `make qemu` | CLI-only | Executable smoke needs RISC-V ELF compiler. |
| Renode | `make renode` | CLI-only | Not installed in fast Docker image; `renode-check` is scaffold only. |
| Buildroot | `make buildroot-check` and `sw/buildroot/scripts/import-buildroot-external.sh` | CLI-only | Full image build needs external Buildroot checkout. |
| Linux kernel | `make linux-bsp-check` | CLI-only | Full kernel build needs external kernel tree/toolchain. |
| AOSP/Cuttlefish | `make aosp-bsp-check`, runbook in `docs/android` | CLI-only | Full build needs external AOSP checkout and Cuttlefish deps. |
| CoreMark | `make benchmarks-dry-run`, `make benchmarks` | CLI-only | `coremark` binary not installed by default. |
| STREAM | `make benchmarks-dry-run`, `make benchmarks` | CLI-only | `stream_c.exe` not installed by default. |
| lmbench | `make benchmarks-dry-run`, `make benchmarks` | CLI-only | `bw_mem` and `lat_mem_rd` not installed by default. |
| fio | `benchmarks/configs/*.fio` | CLI-only | `fio` not installed by default. |
| TFLite benchmark | `benchmark_model` via benchmark harness | CLI-only | Binary and `mobile_smoke.tflite` artifact absent. |
| MLPerf Mobile | Benchmark methodology docs | CLI-capable | Not wired as a local repo command yet. |
| OpenLane | `make openlane` | CLI-only | Docker image or local OpenLane install required. |
| OpenROAD | `make openroad` | CLI-only | Local OpenROAD install required. |
| KiCad | `board/kicad/**` notes only | CLI-capable through `kicad-cli` | No real KiCad project yet. |
| OpenOCD | referenced bring-up tool | CLI-only | No board/JTAG target config yet. |
| sigrok-cli | referenced bring-up tool | CLI-only | No capture profile yet. |
| FreeCAD | referenced mechanical tool | CLI-capable through `FreeCADCmd` | No mechanical model yet. |

## Required Rule

No milestone may be marked complete because a GUI action was possible. Completion
requires one of:

- a repo command that runs headlessly,
- a dry-run command that reports missing dependencies,
- a blocked gate with the exact command and artifact needed to unblock it.

## Current CLI Smoke Set

```sh
make smoke
make benchmarks-dry-run
make software-bsp-check aosp-bsp-check qemu-check renode-check
docker run --rm -v "$PWD:/work" -w /work openphone-soc-tools make ci-fast
```
