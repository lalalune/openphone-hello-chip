#!/usr/bin/env sh
set -eu

if ! command -v make >/dev/null 2>&1; then
    echo "make is required for cocotb"
    exit 1
fi

PYTHON_BIN="${PYTHON:-python3}"

if ! "$PYTHON_BIN" -c "import cocotb" >/dev/null 2>&1; then
    if ! python3 -c "import cocotb" >/dev/null 2>&1; then
        echo "cocotb is not installed. Use Docker/Nix or install cocotb in a virtualenv."
        exit 1
    fi
fi

if command -v verilator >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=verilator
elif command -v iverilog >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=icarus
else
    echo "No cocotb simulator found. Install Verilator or Icarus Verilog."
    exit 1
fi
