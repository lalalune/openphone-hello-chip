# SPDX-License-Identifier: GPL-2.0-only
#
# OpenAgent e1 BSP drivers. Import into an external Linux tree at
# drivers/misc/openagent/ and add `obj-$(CONFIG_OPENAGENT_E1) += openagent/`
# from drivers/misc/Makefile.

obj-$(CONFIG_OPENAGENT_E1_NPU)     += openagent-e1-npu.o
obj-$(CONFIG_OPENAGENT_E1_DMA)     += openagent-e1-dma.o
obj-$(CONFIG_OPENAGENT_E1_DISPLAY) += openagent-e1-display.o
obj-$(CONFIG_OPENAGENT_E1_GPIO)    += openagent-e1-gpio.o

ccflags-y += -I$(src)
