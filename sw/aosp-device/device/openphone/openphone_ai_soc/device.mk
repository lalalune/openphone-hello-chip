# Device makefile for the OpenAgent e1 AI SoC AOSP target.
#
# HAL implementation source lives under:
#   device/openagent/openagent_ai_soc/hal/
#
# Hardware register layout source of truth:
#   sw/platform/e1_platform_contract.json

PRODUCT_DEVICE := openagent_ai_soc
PRODUCT_NAME := openagent_ai_soc
PRODUCT_BRAND := OpenAgent
PRODUCT_MODEL := OpenAgent e1 AI SoC
PRODUCT_MANUFACTURER := OpenAgent

# Init, fstab, VINTF manifest.
PRODUCT_COPY_FILES += \
    device/openagent/openagent_ai_soc/init.openagent.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/init.openagent.rc \
    device/openagent/openagent_ai_soc/fstab.openagent:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.openagent

# HAL service binaries.
#
# Future integration points:
#   android.hardware.graphics.composer@2.4-service
#   hwcomposer.openagent_ai_soc
#   e1_npu.default
# HAL package names are intentionally not listed until source or prebuilts are
# imported into the external AOSP tree. Keeping these out of PRODUCT_PACKAGES
# prevents vendorimage from passing with misleading, unimplemented services.
#
# Future external-tree packages:
#   hwcomposer.openagent_ai_soc
#   e1_npu.default
#
# WiFi/Bluetooth packages, permissions, overlays, supplicant/hostapd configs,
# and Android feature XML are intentionally absent until the external module
# has host-controller, firmware, regulatory, and framework evidence.

PRODUCT_VENDOR_PROPERTIES += \
    ro.soc.manufacturer=OpenAgent \
    ro.soc.model=openagent_ai_soc \
    vendor.e1_npu.ready=0 \
    ro.hardware.hwcomposer=openagent \
    ro.hardware.gralloc=openagent
