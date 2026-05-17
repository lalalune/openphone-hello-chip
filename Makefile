SHELL := /bin/sh

PYTHON ?= python3
RTL_TOP := hello_chip_top
RTL_SRCS := rtl/top/hello_chip_top.sv rtl/clock/hello_reset_sync.sv rtl/debug/hello_dbg_mmio_bridge.sv rtl/top/hello_soc_top.sv rtl/bootrom/hello_bootrom.sv rtl/dma/hello_dma.sv rtl/npu/hello_npu.sv rtl/display/hello_display.sv rtl/peripherals/hello_peripherals.sv rtl/cpu/hello_cpu_subsystem_stub.sv rtl/interconnect/hello_axi_lite_interconnect.sv rtl/memory/hello_axi_lite_dram.sv rtl/interrupts/hello_interrupt_controller.sv rtl/interconnect/hello_linux_soc_contract.sv
BUILD := build

.PHONY: tools smoke ci-fast ci-local ci-strict ci-pd product-check pinout-check fpga-check wifi-interface-check padframe-check pd-contract-check pd-signoff-manifest-check pd-signoff-check rtl-check cocotb cocotb-contract verilator formal synth openlane openroad qemu renode qemu-check renode-check platform-contract-check software-contract-check buildroot-check linux-bsp-check aosp-bsp-check software-bsp-check docs-check tool-versions pipeline-check archive-release clean

tools:
	@scripts/check_tools.sh

smoke: docs-check platform-contract-check rtl-check synth
	@echo "smoke complete"

ci-fast: docs-check platform-contract-check pinout-check rtl-check synth cocotb cocotb-contract verilator formal product-check
	@echo "ci-fast complete"

ci-local: docs-check platform-contract-check pinout-check product-check rtl-check synth cocotb cocotb-contract verilator formal tool-versions
	@echo "ci-local complete"

ci-strict: REQUIRE_SBY=1
ci-strict: ci-local
	@$(PYTHON) scripts/pipeline_check.py
	@echo "ci-strict complete"

ci-pd: openlane pd-signoff-check
	@echo "ci-pd complete"

product-check: pinout-check fpga-check wifi-interface-check padframe-check pd-signoff-manifest-check
	@$(PYTHON) scripts/product_check.py

pinout-check:
	@$(PYTHON) package/scripts/validate_pinout.py package/hello-demo-pinout.yaml

fpga-check:
	@$(PYTHON) scripts/check_fpga_target.py

wifi-interface-check:
	@$(PYTHON) scripts/check_wifi_interface.py

padframe-check:
	@$(PYTHON) scripts/check_padframe_contract.py

pd-contract-check: padframe-check pd-signoff-manifest-check
	@echo "pd contract checks complete"

pd-signoff-manifest-check:
	@$(PYTHON) scripts/check_pd_signoff.py --manifest-only

pd-signoff-check:
	@$(PYTHON) scripts/check_pd_signoff.py

rtl-check:
	@scripts/run_rtl_check.sh

cocotb:
	@scripts/run_cocotb.sh

cocotb-contract:
	@COCOTB_MODULE=test_cpu_mem_intc_contract COCOTB_TOPLEVEL=hello_linux_soc_contract scripts/run_cocotb.sh

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
	@echo "qemu-virt scaffold check complete"

renode-check: platform-contract-check
	@echo "renode qemu-virt scaffold check complete"

platform-contract-check:
	@$(PYTHON) scripts/check_platform_contract.py

software-contract-check: platform-contract-check

buildroot-check:
	@$(PYTHON) scripts/check_software_bsp.py buildroot

linux-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py linux

aosp-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py aosp

software-bsp-check:
	@$(PYTHON) scripts/check_software_bsp.py all

docs-check:
	@$(PYTHON) scripts/docs_check.py

tool-versions:
	@scripts/tool_versions.sh

pipeline-check:
	@$(PYTHON) scripts/pipeline_check.py

archive-release: pipeline-check
	@scripts/archive_release.sh

clean:
	rm -rf $(BUILD) sim_build results reports verify/formal/work verify/cocotb/sim_build verify/cocotb/results.xml verify/formal/hello_dbg_mmio_bridge verify/formal/hello_npu verify/formal/hello_dma verify/formal/hello_soc_top
