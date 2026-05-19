################################################################################
#
# hello-npu-ml-smoke
#
################################################################################

HELLO_NPU_ML_SMOKE_VERSION = 1.0
HELLO_NPU_ML_SMOKE_SITE = $(BR2_EXTERNAL_OPENPHONE_HELLO_PATH)/package/hello-npu-ml-smoke/src
HELLO_NPU_ML_SMOKE_SITE_METHOD = local
HELLO_NPU_ML_SMOKE_LICENSE = GPL-2.0-only
HELLO_NPU_ML_SMOKE_LICENSE_FILES = LICENSE

define HELLO_NPU_ML_SMOKE_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -O2 \
		-o $(@D)/hello-npu-ml-smoke $(@D)/hello-npu-ml-smoke.c
endef

define HELLO_NPU_ML_SMOKE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/hello-npu-ml-smoke \
		$(TARGET_DIR)/usr/bin/hello-npu-ml-smoke
endef

$(eval $(generic-package))
