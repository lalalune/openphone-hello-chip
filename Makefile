SHELL := /bin/sh

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
BENCH_PYTHON := $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(PYTHON))
RTL_TOP := hello_chip_top
RTL_SRCS := rtl/top/hello_chip_top.sv rtl/clock/hello_reset_sync.sv rtl/debug/hello_dbg_mmio_bridge.sv rtl/top/hello_soc_top.sv rtl/bootrom/hello_bootrom.sv rtl/dma/hello_dma.sv rtl/npu/hello_npu.sv rtl/display/hello_display.sv rtl/peripherals/hello_peripherals.sv rtl/cpu/hello_cpu_subsystem_stub.sv rtl/interconnect/hello_axi_lite_interconnect.sv rtl/memory/hello_axi_lite_dram.sv rtl/interrupts/hello_interrupt_controller.sv rtl/interconnect/hello_linux_soc_contract.sv
BUILD := build

.PHONY: ci-release-evidence evidence-regression-test formal-fast formal-strict physical-gates-test pipeline-check-strict strict-release-gate-test

.PHONY: venv tools lint lint-fix typecheck analysis verify-all smoke ci-fast ci-local ci-strict ci-pd benchmarks-dry-run benchmarks benchmark-tools benchmark-sim-metrics benchmark-sim-metrics-test benchmark-calibration-test benchmark-parser-test mvp-status mvp-status-strict mvp-status-json mvp-simulator mvp-simulator-check chipyard-generator-check chipyard-generated-check cpu-ap-scaffold-check cpu-ap-evidence-check cpu-ap-evidence-test cpu-ap-completion-gate no-hardware-action-check memory-uma-claim-gate memory-interconnect-contract-check npu-2028-target-check npu-runtime-contract-check npu-roadmap-check npu-open-scale-model-check npu-scale-sim-check scale-feasibility-gate verification-maturity-matrix-check project-plan-check prototype-status-dashboard-check phone-soc-claim-check product-feature-gates-check product-check product-release-check pinout-check fpga-check fpga-release-check wifi-interface-check padframe-check board-package-evidence-check package-cross-probe-check kicad-artifact-check openlane-run-preflight-check physical-closure-work-order-check manufacturing-artifacts-check manufacturing-artifacts-release-check kicad-artifacts-check package-artifacts-check fpga-artifacts-check real-world-gates-check pd-preflight-check pd-contract-check pd-signoff-manifest-check pd-signoff-check bootrom-check rtl-check stub-audit cocotb cocotb-contract cocotb-cpu verilator formal synth openlane openlane-smoke openroad qemu renode qemu-check qemu-check-strict qemu-os-check qemu-status-test renode-check renode-check-strict renode-status-test android-sim-boot-check android-sim-status-test platform-contract-check software-contract-check buildroot-check buildroot-scaffold-check buildroot-import-check linux-bsp-check linux-scaffold-check linux-import-check aosp-bsp-check aosp-scaffold-check aosp-import-check bsp-scaffold-check software-bsp-check software-bsp-scaffold-check software-bsp-evidence-check software-bsp-test docs-check tool-versions record-tool-versions pipeline-check archive-check archive-release clean

venv:
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_PYTHON) -m pip install --upgrade pip
	@$(VENV_PYTHON) -m pip install -r requirements.txt

tools:
	@scripts/check_tools.sh

lint:
	@$(PYTHON) scripts/run_lint.py

lint-fix:
	@$(PYTHON) scripts/run_lint.py --fix

typecheck:
	@$(PYTHON) scripts/run_typecheck.py

analysis:
	@$(PYTHON) scripts/run_analysis.py

verify-all: lint typecheck smoke analysis cocotb cocotb-contract cocotb-cpu qemu-status-test renode-status-test
	@echo "verify-all complete"

smoke: lint typecheck docs-check project-plan-check prototype-status-dashboard-check npu-2028-target-check npu-runtime-contract-check npu-roadmap-check npu-open-scale-model-check npu-scale-sim-check scale-feasibility-gate verification-maturity-matrix-check platform-contract-check memory-interconnect-contract-check chipyard-generator-check cpu-ap-scaffold-check cpu-ap-evidence-test cpu-ap-completion-gate stub-audit bsp-scaffold-check software-bsp-check qemu-check renode-check benchmarks-dry-run rtl-check synth
	@echo "smoke complete"

ci-fast: lint typecheck docs-check project-plan-check prototype-status-dashboard-check npu-2028-target-check npu-runtime-contract-check npu-roadmap-check npu-open-scale-model-check npu-scale-sim-check scale-feasibility-gate verification-maturity-matrix-check platform-contract-check pinout-check stub-audit rtl-check synth cocotb cocotb-contract cocotb-cpu verilator formal product-check
	@echo "ci-fast complete"

ci-local: lint typecheck docs-check prototype-status-dashboard-check platform-contract-check pinout-check product-check rtl-check synth cocotb cocotb-contract cocotb-cpu verilator formal tool-versions
	@echo "ci-local complete"

ci-strict: REQUIRE_SBY=1
ci-strict: ci-local
	@$(PYTHON) scripts/pipeline_check.py
	@echo "ci-strict complete"

ci-release-evidence: REQUIRE_SBY=1
ci-release-evidence: REQUIRE_DEEP_FORMAL=1
ci-release-evidence: docs-check project-plan-check prototype-status-dashboard-check platform-contract-check pinout-check stub-audit rtl-check synth cocotb cocotb-contract cocotb-cpu verilator formal-strict product-release-check tool-versions pipeline-check-strict
	@echo "ci-release-evidence complete"

ci-pd: openlane pd-signoff-check
	@echo "ci-pd complete"

benchmarks-dry-run:
	@PATH="$(CURDIR)/$(VENV)/bin:$$PATH" $(BENCH_PYTHON) benchmarks/run_benchmarks.py --dry-run --report-id dry-run

benchmark-tools:
	@$(BENCH_PYTHON) benchmarks/install_host_benchmark_tools.py
	@$(BENCH_PYTHON) benchmarks/models/generate_mobile_smoke_tflite.py --out benchmarks/models/mobile_smoke.tflite --status-json benchmarks/results/tflite-generator-status.json

benchmark-sim-metrics: qemu-check
	@$(PYTHON) benchmarks/generate_simulator_arch_metrics.py

benchmark-sim-metrics-test:
	@$(PYTHON) scripts/test_simulator_arch_metrics.py

benchmark-calibration-test:
	@$(PYTHON) scripts/test_benchmark_calibration.py

benchmark-parser-test:
	@$(PYTHON) scripts/test_benchmark_parsers.py

benchmarks:
	@PATH="$(CURDIR)/$(VENV)/bin:$$PATH" $(BENCH_PYTHON) benchmarks/run_benchmarks.py

mvp-status:
	@$(PYTHON) scripts/check_mvp_status.py

mvp-status-strict:
	@$(PYTHON) scripts/check_mvp_status.py --strict

mvp-status-json:
	@mkdir -p build/reports
	@$(PYTHON) scripts/check_mvp_status.py --json | tee build/reports/mvp_status.json

mvp-simulator:
	@$(PYTHON) scripts/run_mvp_simulator.py

mvp-simulator-check:
	@$(PYTHON) scripts/check_mvp_simulator.py

chipyard-generator-check:
	@$(PYTHON) scripts/check_chipyard_generator_manifest.py

chipyard-generated-check:
	@$(PYTHON) scripts/check_chipyard_generator_manifest.py --require-generated

cpu-ap-scaffold-check:
	@$(PYTHON) scripts/check_cpu_ap_evidence.py

cpu-ap-evidence-check:
	@$(PYTHON) scripts/check_cpu_ap_evidence.py --require-evidence

cpu-ap-evidence-test:
	@$(PYTHON) scripts/test_cpu_ap_evidence.py

cpu-ap-completion-gate:
	@$(PYTHON) scripts/check_cpu_ap_completion_gate.py

no-hardware-action-check:
	@$(PYTHON) scripts/check_no_hardware_action_matrix.py

memory-uma-claim-gate:
	@$(PYTHON) scripts/check_memory_uma_claim_gate.py

memory-interconnect-contract-check:
	@$(PYTHON) scripts/check_memory_interconnect_contract.py

npu-2028-target-check:
	@$(PYTHON) scripts/check_npu_2028_targets.py

npu-runtime-contract-check:
	@$(PYTHON) scripts/check_hello_npu_runtime_contract.py

npu-roadmap-check:
	@$(PYTHON) scripts/check_npu_roadmap.py

npu-open-scale-model-check:
	@$(PYTHON) scripts/check_npu_open_scale_model.py

npu-scale-sim-check:
	@$(PYTHON) scripts/check_npu_scale_sim.py

scale-feasibility-gate:
	@$(PYTHON) scripts/check_scale_feasibility_gate.py

verification-maturity-matrix-check:
	@$(PYTHON) scripts/check_verification_maturity_matrix.py

product-check: pinout-check fpga-check wifi-interface-check padframe-check board-package-evidence-check package-cross-probe-check kicad-artifact-check openlane-run-preflight-check physical-closure-work-order-check pd-signoff-manifest-check manufacturing-artifacts-check real-world-gates-check memory-uma-claim-gate memory-interconnect-contract-check product-feature-gates-check
	@$(PYTHON) scripts/product_check.py

product-release-check: pinout-check fpga-check wifi-interface-check padframe-check board-package-evidence-check package-cross-probe-check kicad-artifact-check openlane-run-preflight-check physical-closure-work-order-check pd-signoff-manifest-check manufacturing-artifacts-check real-world-gates-check memory-uma-claim-gate memory-interconnect-contract-check product-feature-gates-check
	@$(PYTHON) scripts/product_check.py --release

project-plan-check:
	@$(PYTHON) scripts/check_project_plan.py

prototype-status-dashboard-check:
	@$(PYTHON) scripts/check_prototype_status_dashboard.py

phone-soc-claim-check:
	@$(PYTHON) scripts/check_phone_soc_claims.py

product-feature-gates-check:
	@$(PYTHON) scripts/check_product_feature_gates.py

pinout-check:
	@$(PYTHON) package/scripts/validate_pinout.py package/hello-demo-pinout.yaml

fpga-check:
	@$(PYTHON) scripts/check_fpga_target.py

fpga-release-check:
	@$(PYTHON) scripts/check_fpga_release.py --release

wifi-interface-check:
	@$(PYTHON) scripts/check_wifi_interface.py

padframe-check:
	@$(PYTHON) scripts/check_padframe_contract.py

board-package-evidence-check:
	@$(PYTHON) scripts/check_board_package_evidence.py

package-cross-probe-check:
	@$(PYTHON) scripts/check_package_cross_probe.py

kicad-artifact-check:
	@$(PYTHON) scripts/check_kicad_artifacts.py

openlane-run-preflight-check:
	@$(PYTHON) scripts/check_openlane_run_preflight.py

physical-closure-work-order-check:
	@$(PYTHON) scripts/check_physical_closure_work_order.py

manufacturing-artifacts-check:
	@$(PYTHON) scripts/check_manufacturing_artifacts.py

manufacturing-artifacts-release-check:
	@$(PYTHON) scripts/check_manufacturing_artifacts.py --release

kicad-artifacts-check:
	@$(PYTHON) scripts/check_manufacturing_artifacts.py --manifest board/kicad/hello-demo/artifact-manifest.yaml

package-artifacts-check:
	@$(PYTHON) scripts/check_manufacturing_artifacts.py --manifest package/artifact-manifest.yaml

fpga-artifacts-check:
	@$(PYTHON) scripts/check_manufacturing_artifacts.py --manifest board/fpga/artifact-manifest.yaml

physical-gates-test:
	@$(PYTHON) scripts/test_physical_gates.py

real-world-gates-check:
	@$(PYTHON) scripts/check_real_world_gates.py

pd-preflight-check:
	@$(PYTHON) scripts/check_pd_preflight.py

pd-contract-check: padframe-check physical-closure-work-order-check pd-preflight-check pd-signoff-manifest-check manufacturing-artifacts-check real-world-gates-check
	@echo "pd contract checks complete"

pd-signoff-manifest-check:
	@$(PYTHON) scripts/check_pd_signoff.py --manifest-only

pd-signoff-check:
	@$(PYTHON) scripts/check_pd_signoff.py

bootrom-check:
	@$(PYTHON) fw/boot-rom/check_boot_rom.py

rtl-check:
	@scripts/run_rtl_check.sh

stub-audit:
	@$(PYTHON) verify/check_stub_audit.py

cocotb:
	@PYTHON=$(VENV_PYTHON) scripts/run_cocotb.sh

cocotb-contract:
	@PYTHON=$(VENV_PYTHON) COCOTB_MODULE=test_cpu_mem_intc_contract COCOTB_TOPLEVEL=hello_linux_soc_contract scripts/run_cocotb.sh

cocotb-cpu:
	@PYTHON=$(VENV_PYTHON) COCOTB_MODULE=test_tiny_cpu_execution COCOTB_TOPLEVEL=hello_tiny_cpu_contract_tb scripts/run_cocotb.sh

verilator:
	@scripts/run_verilator.sh

formal:
	@scripts/run_formal.sh

formal-fast:
	@scripts/run_formal.sh

formal-strict:
	@REQUIRE_SBY=1 REQUIRE_DEEP_FORMAL=1 scripts/run_formal.sh

synth:
	@scripts/run_yosys.sh

openlane:
	@scripts/run_openlane.sh

openlane-smoke:
	@OPENLANE_CONFIG=pd/openlane/config.pd-smoke.sky130.json scripts/run_openlane.sh

openroad:
	@scripts/run_openroad.sh

qemu:
	@scripts/run_qemu.sh

renode:
	@scripts/run_renode.sh

qemu-check: platform-contract-check
	@scripts/run_qemu.sh --check

qemu-check-strict: platform-contract-check
	@REQUIRE_QEMU=1 scripts/run_qemu.sh --check

qemu-os-check: platform-contract-check
	@scripts/run_qemu.sh --check-os

qemu-status-test:
	@$(PYTHON) scripts/test_qemu_smoke_status.py

renode-check: platform-contract-check
	@scripts/run_renode.sh --check

renode-check-strict: platform-contract-check
	@REQUIRE_RENODE=1 scripts/run_renode.sh --check

renode-status-test:
	@$(PYTHON) scripts/test_renode_status.py

android-sim-boot-check:
	@scripts/boot_android_simulator.sh --run-cuttlefish --run-cts --run-vts

android-sim-status-test:
	@$(PYTHON) scripts/test_android_sim_boot_status.py

platform-contract-check:
	@$(PYTHON) scripts/check_platform_contract.py

software-contract-check: platform-contract-check

buildroot-check:
	@$(PYTHON) scripts/check_software_bsp.py buildroot

buildroot-scaffold-check:
	@$(PYTHON) scripts/check_software_bsp.py buildroot --scaffold-only

buildroot-import-check:
	@if [ -z "$${BUILDROOT_TREE:-}" ]; then \
		echo "STATUS: BLOCKED buildroot.import-check - set BUILDROOT_TREE=/path/to/buildroot"; \
		exit 0; \
	fi; \
	sw/buildroot/scripts/import-buildroot-external.sh --check "$$BUILDROOT_TREE"

linux-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py linux

linux-scaffold-check:
	@$(PYTHON) scripts/check_software_bsp.py linux --scaffold-only

linux-import-check:
	@if [ -z "$${LINUX_TREE:-}" ]; then \
		echo "STATUS: BLOCKED linux.import-check - set LINUX_TREE=/path/to/linux"; \
		exit 0; \
	fi; \
	sw/linux/scripts/import-linux-bsp.sh --check "$$LINUX_TREE"

aosp-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py aosp

aosp-scaffold-check:
	@$(PYTHON) scripts/check_software_bsp.py aosp --scaffold-only

aosp-import-check:
	@if [ -z "$${AOSP_TREE:-}" ]; then \
		echo "STATUS: BLOCKED aosp.import-check - set AOSP_TREE=/path/to/aosp"; \
		exit 0; \
	fi; \
	sw/aosp-device/import-aosp-device.sh --check "$$AOSP_TREE"

bsp-scaffold-check:
	@$(PYTHON) sw/check_bsp_scaffolds.py all

software-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py all

software-bsp-scaffold-check:
	@$(PYTHON) scripts/check_software_bsp.py all --scaffold-only

software-bsp-evidence-check:
	@$(PYTHON) scripts/check_software_bsp.py all --require-evidence

software-bsp-test:
	@$(PYTHON) scripts/test_software_bsp_checks.py

evidence-regression-test: no-hardware-action-check software-bsp-test physical-gates-test product-feature-gates-check benchmark-sim-metrics-test benchmark-calibration-test benchmark-parser-test renode-status-test strict-release-gate-test
	@echo "evidence regression tests complete"

docs-check:
	@$(PYTHON) scripts/docs_check.py

tool-versions:
	@scripts/tool_versions.sh

record-tool-versions:
	@mkdir -p build/reports
	@scripts/tool_versions.sh > build/reports/tool_versions.txt

pipeline-check:
	@$(PYTHON) scripts/pipeline_check.py

pipeline-check-strict:
	@$(PYTHON) scripts/pipeline_check.py --strict-formal

strict-release-gate-test:
	@$(PYTHON) scripts/test_strict_release_gates.py

archive-release: pipeline-check
	@scripts/archive_release.sh

archive-check:
	@$(PYTHON) scripts/check_release_archive.py $(ARCHIVE)

clean:
	rm -rf $(BUILD) sim_build sim_build_* results reports verify/formal/work verify/cocotb/sim_build verify/cocotb/sim_build_* verify/cocotb/results.xml verify/formal/hello_dbg_mmio_bridge verify/formal/hello_npu verify/formal/hello_dma verify/formal/hello_soc_top
