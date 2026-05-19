# Board config scaffold for the OpenAgent e1 AOSP target.
#
# This belongs in an external AOSP tree at device/openagent/openagent_ai_soc.
# It references the local BSP contract source:
#   sw/platform/e1_platform_contract.json

TARGET_BOARD_PLATFORM := openagent_ai_soc
TARGET_ARCH := riscv64
TARGET_ARCH_VARIANT :=
TARGET_CPU_ABI := riscv64
TARGET_CPU_VARIANT := generic

# Temporary workaround matching AOSP riscv64 targets while prebuilts lack
# riscv64 variants.
ALLOW_MISSING_DEPENDENCIES := true
TARGET_NO_BOOTLOADER := true
TARGET_NO_KERNEL := false
BOARD_KERNEL_CMDLINE := console=ttyS0 earlycon androidboot.hardware=openagent_ai_soc
BOARD_KERNEL_SEPARATED_DTBO := false
BOARD_VENDOR_SEPOLICY_DIRS += device/openagent/openagent_ai_soc/sepolicy
BOARD_SEPOLICY_M4DEFS += e1_npu=true
DEVICE_MANIFEST_FILE += device/openagent/openagent_ai_soc/manifest.xml
BOARD_USES_GENERIC_KERNEL_IMAGE := true
TARGET_COPY_OUT_VENDOR := vendor

# Scaffold inputs for the external Android kernel/device-tree integration.
# The exact AOSP build variables depend on the selected kernel build flow.
OPENAGENT_KERNEL_CONFIG_FRAGMENT := device/openagent/openagent_ai_soc/kernel/openagent_ai_soc.fragment
OPENAGENT_DTS := device/openagent/openagent_ai_soc/dts/openagent-e1-android.dts
