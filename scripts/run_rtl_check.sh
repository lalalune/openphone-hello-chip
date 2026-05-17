#!/usr/bin/env sh
set -eu

mkdir -p build
repo_dir="$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)"
if [ -d "$repo_dir/tools/bin" ]; then
    PATH="$repo_dir/tools/bin:$PATH"
fi
if [ "$(uname -s)" = "Darwin" ] && [ -d "$repo_dir/external/oss-cad-suite/bin" ]; then
    PATH="$repo_dir/external/oss-cad-suite/bin:$PATH"
fi

rtl_sources="
rtl/top/hello_chip_top.sv
rtl/clock/hello_reset_sync.sv
rtl/debug/hello_dbg_mmio_bridge.sv
rtl/top/hello_soc_top.sv
rtl/bootrom/hello_bootrom.sv
rtl/peripherals/hello_peripherals.sv
rtl/dma/hello_dma.sv
rtl/npu/hello_npu.sv
rtl/display/hello_display.sv
rtl/cpu/hello_cpu_subsystem_stub.sv
rtl/interconnect/hello_axi_lite_interconnect.sv
rtl/memory/hello_axi_lite_dram.sv
rtl/interrupts/hello_interrupt_controller.sv
rtl/interconnect/hello_linux_soc_contract.sv
"

if command -v verilator >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    verilator --lint-only -Wall --top-module hello_chip_top $rtl_sources
elif command -v iverilog >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    iverilog -g2012 -tnull -s hello_chip_top $rtl_sources
else
    echo "STATUS: BLOCKED rtl.check - No local RTL checker found. Install Verilator or Icarus Verilog, or use the Docker/Nix shell."
    if [ "${REQUIRE_RTL_CHECK:-0}" = "1" ]; then
        exit 2
    fi
    exit 0
fi
