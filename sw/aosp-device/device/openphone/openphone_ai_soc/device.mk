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

# HAL packages are intentionally not enabled in the repo-local scaffold.
# Enable these only in an external AOSP tree after source or reviewed prebuilts
# exist and the vendorimage, VINTF, SELinux, and smoke evidence logs are
# archived under docs/evidence/android/.
#
# Future integration points:
#   android.hardware.graphics.composer@2.4-service
#   hwcomposer.openphone_ai_soc
#   hello_npu.default

PRODUCT_VENDOR_PROPERTIES += \
    ro.soc.manufacturer=OpenPhone \
    ro.soc.model=openphone_ai_soc \
    ro.hardware=openphone_ai_soc \
    vendor.hello_npu.ready=0
