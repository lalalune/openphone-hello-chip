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
docs/arch/debug.md
docs/arch/memory-map.md
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
docs/package/hello-demo-package.md
docs/package/hello-demo-pad-ring.md
pd/pin_order.cfg
pd/constraints/hello_soc.sdc
pd/constraints/hello_soc_gf180.sdc
docs/manufacturing/release-manifest.yaml
docs/manufacturing/hello-demo-checklist.md
docs/manufacturing/real-world-verification-gaps.yaml
docs/manufacturing/physical-closure-work-order.yaml
docs/toolchain/README.md
docs/toolchain/headless-cli-audit.md
docs/spec-db/mobile-sota-2026.yaml
docs/benchmarks/benchmark-matrix.md
docs/benchmarks/harness.md
docs/benchmarks/report-schema.yaml
docs/android/riscv-bringup.md
docs/project/three-week-execution-plan.md
docs/project/workstreams.md
docs/risks/risk-register.md
docs/rtl/open_rtl_prototype_path.md
benchmarks/configs/benchmark_plan.json
benchmarks/configs/fio-rand-rw.fio
benchmarks/configs/fio-seq-read.fio
benchmarks/install_host_benchmark_tools.py
benchmarks/metadata/local-host-smoke.json
benchmarks/models/mobile_smoke.tflite
benchmarks/tools/coremark
benchmarks/tools/stream_c.exe
benchmarks/tools/bw_mem
benchmarks/tools/lat_mem_rd
benchmarks/tools/benchmark_model
docs/benchmarks/models/README.md
benchmarks/run_benchmarks.py
board/README.md
docs/board/fpga/README.md
board/fpga/hello_demo_fpga.yaml
board/fpga/constraints/hello_demo_ulx3s.lpf
docs/board/kicad/hello-demo/fab-notes.md
docs/fw/board-smoke/tests/smoke_plan.md
scripts/check_cocotb_results.py
scripts/check_mvp_status.py
scripts/check_project_plan.py
scripts/check_real_world_gates.py
scripts/check_physical_closure_work_order.py
scripts/check_software_bsp.py
scripts/pipeline_check.py
scripts/run_cocotb.sh
scripts/run_formal.sh
scripts/run_qemu.sh
scripts/run_renode.sh
scripts/tool_versions.sh
scripts/yosys_formal_npu_structural.ys
scripts/yosys_formal_top_structural.ys
sw/platform/hello_platform_contract.json
sw/platform/generated/hello_platform_contract.h
sw/bootrom/hello_qemu_firmware.S
sw/bootrom/linker.ld
docs/sw/aosp-device/README.md
sw/aosp-device/import-aosp-device.sh
sw/aosp-device/manifests/openphone-ai-soc-local.xml
sw/aosp-device/device/openphone/openphone_ai_soc/AndroidProducts.mk
sw/aosp-device/device/openphone/openphone_ai_soc/openphone_ai_soc.mk
sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk
sw/aosp-device/device/openphone/openphone_ai_soc/device.mk
sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc
sw/aosp-device/device/openphone/openphone_ai_soc/fstab.openphone
sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml
sw/aosp-device/device/openphone/openphone_ai_soc/kernel/openphone_ai_soc.fragment
sw/aosp-device/device/openphone/openphone_ai_soc/dts/openphone-hello-android.dts
sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts
sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/hello_npu.te
docs/sw/buildroot/README.md
sw/buildroot/external.desc
sw/buildroot/Config.in
sw/buildroot/external.mk
sw/buildroot/configs/openphone_hello_defconfig
sw/buildroot/scripts/import-buildroot-external.sh
sw/buildroot/board/openphone/hello/linux.fragment
sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke
sw/check_bsp_scaffolds.py
docs/sw/linux/README.md
sw/linux/dts/openphone-hello.dts
sw/linux/drivers/hello/Kconfig
sw/linux/drivers/hello/Makefile
sw/linux/drivers/hello/hello-npu.c
sw/linux/drivers/hello/hello-dma.c
sw/linux/scripts/import-linux-bsp.sh
sw/linux/tests/hello-mmio-smoke.c
docs/sw/opensbi/README.md
docs/sw/u-boot/README.md
verify/check_stub_audit.py
verify/cocotb/hello_tiny_cpu_contract_tb.sv
verify/cocotb/test_cpu_mem_intc_contract.py
verify/cocotb/test_hello_display.py
verify/cocotb/test_hello_npu.py
verify/cocotb/test_hello_soc.py
verify/cocotb/test_tiny_cpu_execution.py
verify/verilator/test_npu_gemm.cpp
EOF

find "$archive_dir" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$archive_dir/SHA256SUMS"
tar -C "$repo_dir/build/release" -czf "$archive_dir.tar.gz" "$(basename "$archive_dir")"

echo "Release archive: $archive_dir.tar.gz"
