SHELL := /bin/sh

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
RTL_TOP := hello_chip_top
RTL_SRCS := rtl/top/hello_chip_top.sv rtl/clock/hello_reset_sync.sv rtl/debug/hello_dbg_mmio_bridge.sv rtl/top/hello_soc_top.sv rtl/bootrom/hello_bootrom.sv rtl/dma/hello_dma.sv rtl/npu/hello_npu.sv rtl/display/hello_display.sv rtl/peripherals/hello_peripherals.sv rtl/cpu/hello_cpu_subsystem_stub.sv rtl/interconnect/hello_axi_lite_interconnect.sv rtl/memory/hello_axi_lite_dram.sv rtl/interrupts/hello_interrupt_controller.sv rtl/interconnect/hello_linux_soc_contract.sv
BUILD := build

.PHONY: venv tools lint lint-fix typecheck analysis verify-all smoke ci-fast ci-local ci-strict ci-pd benchmarks-dry-run benchmarks mvp-status mvp-status-strict mvp-status-json chipyard-generator-check chipyard-generated-check cpu-ap-scaffold-check cpu-ap-evidence-check cpu-ap-completion-gate memory-uma-claim-gate npu-2028-target-check project-plan-check product-check product-release-check pinout-check fpga-check fpga-release-check wifi-interface-check padframe-check board-package-evidence-check physical-closure-work-order-check real-world-gates-check pd-preflight-check pd-contract-check pd-signoff-manifest-check pd-signoff-check bootrom-check rtl-check stub-audit cocotb cocotb-contract cocotb-cpu verilator formal synth openlane openroad qemu renode qemu-check qemu-check-strict qemu-status-test renode-check renode-check-strict renode-status-test platform-contract-check software-contract-check buildroot-check linux-bsp-check aosp-bsp-check bsp-scaffold-check software-bsp-check software-bsp-evidence-check docs-check tool-versions record-tool-versions pipeline-check archive-release clean

venv:
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_PYTHON) -m pip install --upgrade pip
	@$(VENV_PYTHON) -m pip install -r requirements.txt
	@scripts/install_benchmark_smoke_tools.sh

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

smoke: lint typecheck docs-check project-plan-check npu-2028-target-check platform-contract-check chipyard-generator-check cpu-ap-scaffold-check cpu-ap-completion-gate bootrom-check stub-audit software-bsp-check qemu-check renode-check benchmarks-dry-run rtl-check synth
	@echo "smoke complete"

ci-fast: lint typecheck docs-check project-plan-check npu-2028-target-check platform-contract-check pinout-check stub-audit rtl-check synth cocotb cocotb-contract cocotb-cpu verilator formal product-check
	@echo "ci-fast complete"

ci-local: lint typecheck docs-check platform-contract-check pinout-check product-check rtl-check synth cocotb cocotb-contract cocotb-cpu verilator formal tool-versions
	@echo "ci-local complete"

ci-strict: REQUIRE_SBY=1
ci-strict: ci-local
	@$(PYTHON) scripts/pipeline_check.py
	@echo "ci-strict complete"

ci-pd: openlane pd-signoff-check
	@echo "ci-pd complete"

benchmarks-dry-run:
	@scripts/install_benchmark_smoke_tools.sh
	@PATH="$(CURDIR)/$(VENV)/bin:$(CURDIR)/benchmarks/tools:$$PATH" $(VENV_PYTHON) benchmarks/run_benchmarks.py --dry-run --report-id dry-run

benchmarks:
	@scripts/install_benchmark_smoke_tools.sh
	@PATH="$(CURDIR)/$(VENV)/bin:$(CURDIR)/benchmarks/tools:$$PATH" $(VENV_PYTHON) benchmarks/run_benchmarks.py --allow-host-smoke-tools

mvp-status:
	@$(PYTHON) scripts/check_mvp_status.py

mvp-status-strict:
	@$(PYTHON) scripts/check_mvp_status.py --strict

# Emit machine-readable JSON (includes evidence_class per row) for CI artifact
# capture. Distinguishes PASS / BLOCK (missing tool or external tree) / FAIL.
mvp-status-json:
	@mkdir -p build/reports
	@$(PYTHON) scripts/check_mvp_status.py --json | tee build/reports/mvp_status.json

chipyard-generator-check:
	@$(PYTHON) scripts/check_chipyard_generator_manifest.py

chipyard-generated-check:
	@$(PYTHON) scripts/check_chipyard_generator_manifest.py --require-generated

cpu-ap-scaffold-check:
	@$(PYTHON) scripts/check_cpu_ap_evidence.py

cpu-ap-evidence-check:
	@$(PYTHON) scripts/check_cpu_ap_evidence.py --require-evidence

cpu-ap-completion-gate:
	@$(PYTHON) scripts/check_cpu_ap_completion_gate.py

memory-uma-claim-gate:
	@$(PYTHON) scripts/check_memory_uma_claim_gate.py

npu-2028-target-check:
	@$(PYTHON) scripts/check_npu_2028_targets.py

product-check: pinout-check fpga-check wifi-interface-check padframe-check board-package-evidence-check physical-closure-work-order-check pd-signoff-manifest-check real-world-gates-check memory-uma-claim-gate
	@$(PYTHON) scripts/product_check.py

product-release-check: pinout-check fpga-check wifi-interface-check padframe-check board-package-evidence-check physical-closure-work-order-check pd-signoff-manifest-check real-world-gates-check memory-uma-claim-gate
	@$(PYTHON) scripts/product_check.py --release

project-plan-check:
	@$(PYTHON) scripts/check_project_plan.py

pinout-check:
	@$(PYTHON) package/scripts/validate_pinout.py package/hello-demo-pinout.yaml

fpga-check:
	@$(PYTHON) scripts/check_fpga_target.py

fpga-release-check: fpga-check
	@$(PYTHON) scripts/check_fpga_release.py

wifi-interface-check:
	@$(PYTHON) scripts/check_wifi_interface.py

padframe-check:
	@$(PYTHON) scripts/check_padframe_contract.py

board-package-evidence-check:
	@$(PYTHON) scripts/check_board_package_evidence.py

physical-closure-work-order-check:
	@$(PYTHON) scripts/check_physical_closure_work_order.py

real-world-gates-check:
	@$(PYTHON) scripts/check_real_world_gates.py

pd-preflight-check:
	@$(PYTHON) scripts/check_pd_preflight.py

pd-contract-check: padframe-check physical-closure-work-order-check pd-preflight-check pd-signoff-manifest-check real-world-gates-check
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

synth:
	@scripts/run_yosys.sh

openlane:
	@scripts/run_openlane.sh

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

qemu-status-test:
	@$(PYTHON) scripts/test_qemu_smoke_status.py

renode-check: platform-contract-check
	@scripts/run_renode.sh --check

renode-check-strict: platform-contract-check
	@REQUIRE_RENODE=1 scripts/run_renode.sh --check

renode-status-test:
	@$(PYTHON) scripts/test_renode_status.py

platform-contract-check:
	@$(PYTHON) scripts/check_platform_contract.py

software-contract-check: platform-contract-check

buildroot-check:
	@$(PYTHON) scripts/check_software_bsp.py buildroot

linux-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py linux

aosp-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py aosp

bsp-scaffold-check:
	@$(PYTHON) sw/check_bsp_scaffolds.py all

software-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py all

software-bsp-evidence-check:
	@$(PYTHON) scripts/check_software_bsp.py all --require-evidence

docs-check:
	@$(PYTHON) scripts/docs_check.py

tool-versions:
	@scripts/tool_versions.sh
	@scripts/record_tool_versions.sh

# Release-gate focused tool manifest. Fail-soft per tool; entries that are
# absent are recorded as MISSING so the artifact is always uploadable.
record-tool-versions:
	@scripts/record_tool_versions.sh

pipeline-check:
	@$(PYTHON) scripts/pipeline_check.py

archive-release: pipeline-check
	@scripts/archive_release.sh

clean:
	rm -rf $(BUILD) sim_build sim_build_* results reports verify/formal/work verify/cocotb/sim_build verify/cocotb/sim_build_* verify/cocotb/results.xml verify/formal/hello_dbg_mmio_bridge verify/formal/hello_npu verify/formal/hello_dma verify/formal/hello_soc_top
