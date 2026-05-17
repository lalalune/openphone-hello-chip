# Buildroot external makefile for the OpenPhone hello BSP.
#
# The external tree supplies board metadata, a Linux config fragment, a rootfs
# overlay, and per-package recipes under package/*/.

include $(sort $(wildcard $(BR2_EXTERNAL_OPENPHONE_HELLO_PATH)/package/*/*.mk))
