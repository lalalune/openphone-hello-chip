# Device makefile scaffold for an external AOSP tree.
#
# The hello_npu and hwcomposer entries are fail-closed HAL integration points;
# the hardware contract remains sw/platform/hello_platform_contract.json.

PRODUCT_DEVICE := openphone_ai_soc
PRODUCT_NAME := openphone_ai_soc
PRODUCT_BRAND := OpenPhone
PRODUCT_MODEL := OpenPhone hello AI SoC
PRODUCT_MANUFACTURER := OpenPhone

PRODUCT_COPY_FILES += \
    device/openphone/openphone_ai_soc/init.openphone.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/init.openphone.rc \
    device/openphone/openphone_ai_soc/fstab.openphone:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.openphone \
    device/openphone/openphone_ai_soc/manifest.xml:$(TARGET_COPY_OUT_VENDOR)/etc/vintf/manifest/openphone_hello.xml

# HAL package names are intentionally not listed until source or prebuilts are
# imported into the external AOSP tree. Keeping these out of PRODUCT_PACKAGES
# prevents vendorimage from passing with misleading, unimplemented services.
#
# Future external-tree packages:
#   hwcomposer.openphone_ai_soc
#   hello_npu.default
#
# WiFi/Bluetooth packages, permissions, overlays, supplicant/hostapd configs,
# and Android feature XML are intentionally absent until the external module
# has host-controller, firmware, regulatory, and framework evidence.

PRODUCT_VENDOR_PROPERTIES += \
    ro.soc.manufacturer=OpenPhone \
    ro.soc.model=openphone_ai_soc \
    vendor.hello_npu.ready=0
