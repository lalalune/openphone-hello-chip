#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "$(uname -s)" = "Darwin" ] && [ -d "$repo_dir/external/oss-cad-suite/bin" ]; then
    PATH="$repo_dir/external/oss-cad-suite/bin:$PATH"
fi

mkdir -p build/reports verify/formal/work

if ! command -v sby >/dev/null 2>&1; then
    if [ "${REQUIRE_SBY:-0}" = "1" ]; then
        echo "SymbiYosys is required for this target; refusing Yosys fallback."
        exit 1
    fi
    if command -v yosys >/dev/null 2>&1; then
        echo "SymbiYosys missing; running Yosys SAT fallback."
        echo "Bridge formal requires SymbiYosys; fallback covers legacy blocks only."
        yosys -q -l build/reports/hello_soc_top_formal_yosys.log scripts/yosys_formal_top_structural.ys
        yosys -q -l build/reports/hello_npu_formal_yosys.log scripts/yosys_formal_npu_structural.ys
        yosys -q -l build/reports/hello_dma_formal_yosys.log scripts/yosys_formal_dma.ys
        echo "Yosys formal fallback reports: build/reports/hello_*_formal_yosys.log"
        exit 0
    fi
    echo "SymbiYosys and Yosys are missing. Use Docker/Nix or add formal tools to PATH."
    exit 1
fi

sby -f verify/formal/hello_dbg_mmio_bridge.sby
sby -f verify/formal/hello_npu.sby
sby -f verify/formal/hello_dma.sby
sby -f verify/formal/hello_soc_top.sby
