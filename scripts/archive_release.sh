#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_dir="$repo_dir/build/release/openphone_hello_demo_$stamp"

mkdir -p "$archive_dir"

if [ -d "$repo_dir/build/reports" ]; then
    cp -R "$repo_dir/build/reports" "$archive_dir/reports"
fi
if [ -d "$repo_dir/build/netlist" ]; then
    cp -R "$repo_dir/build/netlist" "$archive_dir/netlist"
fi
if [ -d "$repo_dir/pd/openlane/runs" ]; then
    mkdir -p "$archive_dir/pd/openlane"
    cp -R "$repo_dir/pd/openlane/runs" "$archive_dir/pd/openlane/runs"
fi

while IFS= read -r path; do
    [ -z "$path" ] && continue
    [ -f "$repo_dir/$path" ] || continue
    mkdir -p "$archive_dir/source/$(dirname "$path")"
    cp "$repo_dir/$path" "$archive_dir/source/$path"
done <<'EOF'
README.md
Makefile
Dockerfile
.github/workflows/ci.yml
arch/debug.md
arch/memory-map.md
rtl/top/hello_chip_top.sv
rtl/debug/hello_dbg_mmio_bridge.sv
rtl/clock/hello_reset_sync.sv
rtl/top/hello_soc_top.sv
rtl/bootrom/hello_bootrom.sv
rtl/peripherals/hello_peripherals.sv
rtl/dma/hello_dma.sv
rtl/npu/hello_npu.sv
rtl/display/hello_display.sv
verify/cocotb/test_hello_chip.py
package/hello-demo-pinout.yaml
package/hello-demo-package.md
package/hello-demo-pad-ring.md
pd/pin_order.cfg
pd/constraints/hello_soc.sdc
pd/constraints/hello_soc_gf180.sdc
docs/manufacturing/release-manifest.yaml
docs/manufacturing/hello-demo-checklist.md
docs/toolchain/README.md
docs/spec-db/mobile-sota-2026.yaml
docs/benchmarks/benchmark-matrix.md
docs/benchmarks/report-schema.yaml
docs/android/riscv-bringup.md
docs/project/three-week-execution-plan.md
docs/project/workstreams.md
docs/risks/risk-register.md
rtl/open_rtl_prototype_path.md
board/README.md
board/fpga/README.md
board/fpga/hello_demo_fpga.yaml
board/fpga/constraints/hello_demo_ulx3s.lpf
board/kicad/hello-demo/fab-notes.md
fw/board-smoke/tests/smoke_plan.md
EOF

find "$archive_dir" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$archive_dir/SHA256SUMS"
tar -C "$repo_dir/build/release" -czf "$archive_dir.tar.gz" "$(basename "$archive_dir")"

echo "Release archive: $archive_dir.tar.gz"
