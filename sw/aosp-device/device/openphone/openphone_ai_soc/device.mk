# Device makefile v0 for openphone_ai_soc.
#
# Backing contract: sw/platform/hello_platform_contract.json
# Status: scaffold for an external AOSP tree. Every HAL listed is a v0
# stub: graphics composer is a framebuffer pass-through with no GLES/Vulkan
# claim, and hello_npu fails closed when /dev/hello-npu is absent.

PRODUCT_DEVICE := openphone_ai_soc
PRODUCT_NAME := openphone_ai_soc
PRODUCT_BRAND := OpenPhone
PRODUCT_MODEL := OpenPhone hello AI SoC
PRODUCT_MANUFACTURER := OpenPhone

# Init, fstab, VINTF manifest.
PRODUCT_COPY_FILES += \
    device/openphone/openphone_ai_soc/init.openphone.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/init.openphone.rc \
    device/openphone/openphone_ai_soc/fstab.openphone:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.openphone \
    device/openphone/openphone_ai_soc/manifest.xml:$(TARGET_COPY_OUT_VENDOR)/etc/vintf/manifest.xml

# v0 HAL packages. Both are stubs and must remain the ONLY HALs declared
# here until backing kernel drivers and CTS/VTS transcripts exist.
PRODUCT_PACKAGES += \
    vendor.openphone.hello_npu@1.0-service \
    android.hardware.graphics.composer@2.4-service.openphone_ai_soc \
    hwcomposer.openphone_ai_soc

# Explicitly NOT declared (v0):
#   audio, camera, radio/telephony, bluetooth, wifi, gnss, nfc, sensors,
#   thermal, power, drm, keymaster/keymint, gatekeeper, biometric, vulkan,
#   neuralnetworks (NNAPI), tv, automotive, secure_element.
# Do not add any of the above without driver evidence, CTS/VTS pass logs,
# and an updated manifest.xml entry.

PRODUCT_VENDOR_PROPERTIES += \
    ro.soc.manufacturer=OpenPhone \
    ro.soc.model=openphone_ai_soc \
    ro.hardware=openphone_ai_soc \
    vendor.hello_npu.ready=0
