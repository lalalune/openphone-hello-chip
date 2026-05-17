# Board config scaffold for the OpenPhone hello AOSP target.
#
# This belongs in an external AOSP tree at device/openphone/openphone_ai_soc.
# It references the local BSP contract source:
#   sw/platform/hello_platform_contract.json

TARGET_BOARD_PLATFORM := openphone_ai_soc
TARGET_ARCH := riscv64
TARGET_ARCH_VARIANT := riscv64
TARGET_CPU_VARIANT := generic
TARGET_NO_BOOTLOADER := true
TARGET_NO_KERNEL := false
BOARD_KERNEL_CMDLINE := console=ttyS0 earlycon androidboot.hardware=openphone_ai_soc
BOARD_KERNEL_SEPARATED_DTBO := false
BOARD_VENDOR_SEPOLICY_DIRS += device/openphone/openphone_ai_soc/sepolicy
BOARD_SEPOLICY_M4DEFS += hello_npu=true
BOARD_USES_GENERIC_KERNEL_IMAGE := true
TARGET_COPY_OUT_VENDOR := vendor

# Scaffold inputs for the external Android kernel/device-tree integration.
# The exact AOSP build variables depend on the selected kernel build flow.
OPENPHONE_KERNEL_CONFIG_FRAGMENT := device/openphone/openphone_ai_soc/kernel/openphone_ai_soc.fragment
OPENPHONE_DTS := device/openphone/openphone_ai_soc/dts/openphone-hello-android.dts
