$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_base.mk)
$(call inherit-product, device/openphone/openphone_ai_soc/device.mk)

PRODUCT_NAME := openphone_ai_soc
PRODUCT_DEVICE := openphone_ai_soc
PRODUCT_BRAND := OpenPhone
PRODUCT_MODEL := OpenPhone hello AI SoC
PRODUCT_MANUFACTURER := OpenPhone
