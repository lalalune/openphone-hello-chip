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
	$(REPO)/rtl/display/hello_display.sv

TOPLEVEL := hello_chip_top
MODULE := test_hello_chip

EXTRA_ARGS += -Wall

include $(shell cocotb-config --makefiles)/Makefile.sim
