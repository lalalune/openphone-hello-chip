# Device makefile for the OpenPhone hello AI SoC AOSP target.
#
# HAL implementation source lives under:
#   device/openphone/openphone_ai_soc/hal/
#
# Hardware register layout source of truth:
#   sw/platform/hello_platform_contract.json

PRODUCT_DEVICE := openphone_ai_soc
PRODUCT_NAME := openphone_ai_soc
PRODUCT_BRAND := OpenPhone
PRODUCT_MODEL := OpenPhone hello AI SoC
PRODUCT_MANUFACTURER := OpenPhone

PRODUCT_COPY_FILES += \
    device/openphone/openphone_ai_soc/init.openphone.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/init.openphone.rc \
    device/openphone/openphone_ai_soc/fstab.openphone:$(TARGET_COPY_OUT_VENDOR)/etc/fstab.openphone \
    device/openphone/openphone_ai_soc/manifest.xml:$(TARGET_COPY_OUT_VENDOR)/etc/vintf/manifest/openphone_hello.xml

# HAL service binaries.
#
# NPU NNAPI 1.3:
#   android.hardware.neuralnetworks@1.3-service.hello_npu
#   Hardware path via /dev/hello-npu (MMIO base 0x10020000).
#   Falls back to CPU reference path when the device node is absent.
#   Service starts only when vendor.hello_npu.ready=1.
#
# HWComposer 2.4:
#   android.hardware.graphics.composer@2.4-service.openphone
#   All layers → CLIENT composition (SurfaceFlinger GPU).
#   VSYNC polled from display MMIO 0x10030000+0x10, bit 0.
#
# Gralloc 4.0:
#   android.hardware.graphics.allocator@4.0-service.openphone  (hwbinder service)
#   android.hardware.graphics.mapper@4.0-impl.openphone        (passthrough, in-process)
#   All allocations backed by ashmem; no hardware memory manager required.
#
# WiFi/Bluetooth/camera/audio/radio/GNSS/NFC/sensors intentionally absent.

PRODUCT_PACKAGES += \
    android.hardware.neuralnetworks@1.3-service.hello_npu \
    android.hardware.graphics.composer@2.4-service.openphone \
    android.hardware.graphics.allocator@4.0-service.openphone \
    android.hardware.graphics.mapper@4.0-impl.openphone

PRODUCT_VENDOR_PROPERTIES += \
    ro.soc.manufacturer=OpenPhone \
    ro.soc.model=openphone_ai_soc \
    vendor.hello_npu.ready=0 \
    ro.hardware.hwcomposer=openphone \
    ro.hardware.gralloc=openphone
