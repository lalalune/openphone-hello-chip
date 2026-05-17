SHELL := /bin/sh

PYTHON ?= python3
RTL_TOP := hello_chip_top
RTL_SRCS := rtl/top/hello_chip_top.sv rtl/clock/hello_reset_sync.sv rtl/debug/hello_dbg_mmio_bridge.sv rtl/top/hello_soc_top.sv rtl/bootrom/hello_bootrom.sv rtl/dma/hello_dma.sv rtl/npu/hello_npu.sv rtl/display/hello_display.sv rtl/peripherals/hello_peripherals.sv
BUILD := build

.PHONY: tools smoke ci-fast ci-local ci-strict ci-pd product-check pinout-check rtl-check cocotb verilator formal synth openlane openroad qemu renode docs-check tool-versions pipeline-check archive-release clean

tools:
	@scripts/check_tools.sh

smoke: docs-check rtl-check synth
	@echo "smoke complete"

ci-fast: docs-check pinout-check rtl-check synth cocotb verilator formal product-check
	@echo "ci-fast complete"

ci-local: docs-check pinout-check product-check rtl-check synth cocotb verilator formal tool-versions
	@echo "ci-local complete"

ci-strict: REQUIRE_SBY=1
ci-strict: ci-local
	@$(PYTHON) scripts/pipeline_check.py
	@echo "ci-strict complete"

ci-pd: openlane
	@echo "ci-pd complete"

product-check: pinout-check
	@$(PYTHON) scripts/product_check.py

pinout-check:
	@$(PYTHON) package/scripts/validate_pinout.py package/hello-demo-pinout.yaml

rtl-check:
	@scripts/run_rtl_check.sh

cocotb:
	@scripts/run_cocotb.sh

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
