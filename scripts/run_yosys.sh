#!/usr/bin/env sh
set -eu

if ! command -v yosys >/dev/null 2>&1; then
    echo "Yosys missing. Use Docker/Nix or install Yosys."
    exit 1
fi

mkdir -p build/reports build/netlist
yosys -q -l build/reports/hello_soc_yosys.log scripts/yosys_hello_soc.ys
echo "Yosys report: build/reports/hello_soc_yosys.log"
