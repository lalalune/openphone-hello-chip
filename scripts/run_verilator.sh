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
    "$repo_dir/rtl/cpu/hello_cva6_wrapper.sv" \
    "$repo_dir/rtl/cpu/hello_cpu_axi_bridge.sv" \
    "$repo_dir/rtl/cpu/hello_cpu_subsystem_stub.sv" \
    "$repo_dir/rtl/interconnect/hello_axi_lite_interconnect.sv" \
    "$repo_dir/rtl/memory/hello_axi_lite_dram.sv" \
    "$repo_dir/rtl/interrupts/hello_interrupt_controller.sv" \
    "$repo_dir/rtl/interconnect/hello_linux_soc_contract.sv" \
    "$repo_dir/sim/verilator/sim_main.cpp" \
    -Mdir build/verilator

build/verilator/Vhello_chip_top

verilator -Wall --cc --exe --build \
    --top-module hello_soc_top \
    "$repo_dir/rtl/top/hello_soc_top.sv" \
    "$repo_dir/rtl/bootrom/hello_bootrom.sv" \
    "$repo_dir/rtl/peripherals/hello_peripherals.sv" \
    "$repo_dir/rtl/dma/hello_dma.sv" \
    "$repo_dir/rtl/npu/hello_npu.sv" \
    "$repo_dir/rtl/display/hello_display.sv" \
    "$repo_dir/rtl/cpu/hello_cva6_wrapper.sv" \
    "$repo_dir/rtl/cpu/hello_cpu_axi_bridge.sv" \
    "$repo_dir/rtl/cpu/hello_cpu_subsystem_stub.sv" \
    "$repo_dir/rtl/interconnect/hello_axi_lite_interconnect.sv" \
    "$repo_dir/rtl/memory/hello_axi_lite_dram.sv" \
    "$repo_dir/rtl/interrupts/hello_interrupt_controller.sv" \
    "$repo_dir/rtl/interconnect/hello_linux_soc_contract.sv" \
    "$repo_dir/verify/verilator/test_npu_gemm.cpp" \
    -Mdir build/verilator_npu_gemm

build/verilator_npu_gemm/Vhello_soc_top
