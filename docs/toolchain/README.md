# Toolchain setup

The project uses two tool tiers:

1. Fast hello-chip tools in `Dockerfile` and `flake.nix`.
2. Heavy SoC/PD/software stacks bootstrapped under `external/` only when needed.

## Fast default image

```sh
docker build -t openphone-soc-tools .
docker run --rm -it -v "$PWD:/work" -w /work openphone-soc-tools make smoke cocotb verilator formal
```

This image currently installs:

```text
Verilator
Yosys
Yosys SMTBMC
Z3
Icarus Verilog
GTKWave
QEMU RISC-V system emulator
Python
cocotb
pytest
numpy
```

## Heavy external stacks

The following tools are intentionally not vendored into the fast image:

| Tool | Bootstrap entry point | Why separate |
| --- | --- | --- |
| Chipyard | `scripts/bootstrap_chipyard.sh` | Large recursive submodule stack |
| Chisel/CIRCT | Chipyard plus `generators/chisel`/`generators/circt` | JVM/LLVM-heavy generator flow |
| OpenLane/OpenROAD full PD | `scripts/bootstrap_openlane2.sh` and `make openlane` | PDK and container-specific flow |
| SymbiYosys | local package/Nix install; `.sby` files are present | Solver packaging varies by OS; Docker carries Z3 for the Yosys fallback |
| Renode | local install; `make renode` uses stubs | Not packaged in the fast image |
| AOSP | future `sw/aosp-device` target | Too large for normal chip CI |

## Current verified path

The default Docker path has been verified through:

```text
docs-check
Verilator lint/elaboration
Yosys synthesis
cocotb register tests
standalone Verilator C++ smoke
Yosys SAT formal fallback
```

OpenLane/OpenROAD targets are wired, but require a local/container OpenLane installation plus an installed PDK.

## OpenLane image

The configured OpenLane2 image is:

```sh
OPENLANE_IMAGE=ghcr.io/efabless/openlane2:2.4.0.dev1
scripts/install_openlane_image.sh
```

Then run:

```sh
OPENLANE_CONFIG=pd/openlane/config.sky130.json make openlane
```

If the image is unavailable or the registry stalls, `make openlane` fails clearly rather than pretending signoff completed.

## FPGA scaffold

The owned FPGA target is documented in `board/fpga/README.md` with contract data in `board/fpga/hello_demo_fpga.yaml`.

Run:

```sh
make fpga-check
```

This validates the FPGA scaffold against the RTL/package interface. It does not build a bitstream; that remains blocked until exact board pins are assigned in the LPF constraints.

## PD gates

Run:

```sh
make pd-contract-check
make ci-pd
```

`pd-contract-check` validates package, padframe, and signoff manifest consistency. `ci-pd` runs OpenLane and then requires signoff artifacts through `scripts/check_pd_signoff.py`.
