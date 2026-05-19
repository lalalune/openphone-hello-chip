$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_base.mk)
$(call inherit-product, device/openagent/openagent_ai_soc/device.mk)

PRODUCT_NAME := openagent_ai_soc
PRODUCT_DEVICE := openagent_ai_soc
PRODUCT_BRAND := OpenAgent
PRODUCT_MODEL := OpenAgent e1 AI SoC
PRODUCT_MANUFACTURER := OpenAgent
