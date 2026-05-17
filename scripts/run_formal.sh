#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "$(uname -s)" = "Darwin" ] && [ -d "$repo_dir/external/oss-cad-suite/bin" ]; then
    PATH="$repo_dir/external/oss-cad-suite/bin:$PATH"
fi

mkdir -p build/reports build/formal verify/formal/work

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

run_sby() {
    name="$1"
    spec="verify/formal/$name.sby"
    prefix="build/formal/${name}.$$"
    canonical="verify/formal/$name"

    rm -rf "$prefix"
    sby --prefix "$prefix" -f "$spec"
    mkdir -p "$canonical"
    cp "$prefix/status" "$canonical/status"
    cp "$prefix/logfile.txt" "$canonical/logfile.txt"
}

run_sby hello_dbg_mmio_bridge
run_sby hello_npu
run_sby hello_dma
if [ "${REQUIRE_DEEP_FORMAL:-0}" = "1" ]; then
    run_sby hello_soc_top
else
    echo "Running structural top-level formal for routine CI. Set REQUIRE_DEEP_FORMAL=1 for the deeper hello_soc_top SymbiYosys BMC."
    yosys -q -l build/reports/hello_soc_top_formal_yosys.log scripts/yosys_formal_top_structural.ys
fi
