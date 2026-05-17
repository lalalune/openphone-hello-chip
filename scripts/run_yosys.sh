#!/usr/bin/env sh
set -eu

if ! command -v yosys >/dev/null 2>&1; then
    echo "STATUS: BLOCKED synth.yosys - Yosys missing. Use Docker/Nix or install Yosys."
    if [ "${REQUIRE_YOSYS:-0}" = "1" ]; then
        exit 2
    fi
    exit 0
fi

mkdir -p build/reports build/netlist
yosys -q -l build/reports/hello_soc_yosys.log scripts/yosys_hello_soc.ys
echo "Yosys report: build/reports/hello_soc_yosys.log"
