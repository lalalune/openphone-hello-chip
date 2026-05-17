#!/usr/bin/env sh
set -eu

if ! command -v verilator >/dev/null 2>&1; then
    echo "Verilator missing. Use Docker/Nix or install Verilator."
    exit 1
fi

rm -rf build/verilator
mkdir -p build/verilator
repo_dir="$(pwd)"
verilator -Wall --cc --exe --build \
    --top-module hello_chip_top \
    "$repo_dir/rtl/top/hello_chip_top.sv" \
    "$repo_dir/rtl/clock/hello_reset_sync.sv" \
    "$repo_dir/rtl/debug/hello_dbg_mmio_bridge.sv" \
    "$repo_dir/rtl/top/hello_soc_top.sv" \
    "$repo_dir/rtl/bootrom/hello_bootrom.sv" \
    "$repo_dir/rtl/peripherals/hello_peripherals.sv" \
    "$repo_dir/rtl/dma/hello_dma.sv" \
    "$repo_dir/rtl/npu/hello_npu.sv" \
    "$repo_dir/rtl/display/hello_display.sv" \
    "$repo_dir/sim/verilator/sim_main.cpp" \
    -Mdir build/verilator

build/verilator/Vhello_chip_top
