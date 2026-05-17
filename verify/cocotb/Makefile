TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)
REPO := $(abspath ../..)

VERILOG_SOURCES := \
	$(REPO)/rtl/top/hello_chip_top.sv \
	$(REPO)/rtl/clock/hello_reset_sync.sv \
	$(REPO)/rtl/debug/hello_dbg_mmio_bridge.sv \
	$(REPO)/rtl/top/hello_soc_top.sv \
	$(REPO)/rtl/bootrom/hello_bootrom.sv \
	$(REPO)/rtl/peripherals/hello_peripherals.sv \
	$(REPO)/rtl/dma/hello_dma.sv \
	$(REPO)/rtl/npu/hello_npu.sv \
	$(REPO)/rtl/display/hello_display.sv \
	$(REPO)/rtl/cpu/hello_cpu_subsystem_stub.sv \
	$(REPO)/rtl/interconnect/hello_axi_lite_interconnect.sv \
	$(REPO)/rtl/memory/hello_axi_lite_dram.sv \
	$(REPO)/rtl/interrupts/hello_interrupt_controller.sv \
	$(REPO)/rtl/interconnect/hello_linux_soc_contract.sv

TOPLEVEL ?= hello_chip_top
MODULE ?= test_hello_chip

EXTRA_ARGS += -Wall

include $(shell cocotb-config --makefiles)/Makefile.sim
