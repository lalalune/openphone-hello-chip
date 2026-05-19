################################################################################
#
# hello-mmio-smoke
#
################################################################################

HELLO_MMIO_SMOKE_VERSION = 1.0
HELLO_MMIO_SMOKE_SITE = $(BR2_EXTERNAL_OPENPHONE_HELLO_PATH)/package/hello-mmio-smoke/src
HELLO_MMIO_SMOKE_SITE_METHOD = local
HELLO_MMIO_SMOKE_LICENSE = GPL-2.0-only
HELLO_MMIO_SMOKE_LICENSE_FILES = LICENSE

define HELLO_MMIO_SMOKE_BUILD_CMDS
	$(TARGET_CC) $(TARGET_CFLAGS) -Wall -O2 \
		-o $(@D)/hello-mmio-smoke $(@D)/hello-mmio-smoke.c
endef

define HELLO_MMIO_SMOKE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/hello-mmio-smoke \
		$(TARGET_DIR)/usr/bin/hello-mmio-smoke
endef

$(eval $(generic-package))
