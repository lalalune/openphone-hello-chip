# SPDX-License-Identifier: GPL-2.0-only
#
# OpenPhone hello BSP drivers. Import into an external Linux tree at
# drivers/misc/openphone/ and add `obj-$(CONFIG_OPENPHONE_HELLO) += openphone/`
# from drivers/misc/Makefile.

obj-$(CONFIG_OPENPHONE_HELLO_NPU)     += openphone-hello-npu.o
obj-$(CONFIG_OPENPHONE_HELLO_DMA)     += openphone-hello-dma.o
obj-$(CONFIG_OPENPHONE_HELLO_DISPLAY) += openphone-hello-display.o
obj-$(CONFIG_OPENPHONE_HELLO_GPIO)    += openphone-hello-gpio.o

ccflags-y += -I$(src)
