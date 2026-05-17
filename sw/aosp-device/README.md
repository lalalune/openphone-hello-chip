# AOSP device target

Future target path:

```text
sw/aosp-device/device/openphone/openphone_ai_soc
```

Initial Android bringup should target QEMU/Renode before RTL simulation, but qemu-virt success is not hardware ABI validation. Device and HAL code must tie back to `sw/platform/hello_platform_contract.json` or generated artifacts from it.

`make aosp-bsp-check` rejects a documentation-only target. The initial Android bring-up target must provide:

```text
BoardConfig.mk
device.mk
init.openphone.rc
manifest.xml
SELinux file_contexts
kernel config
device tree
init files
fstab
SELinux policy
HAL stubs
framebuffer/display path
NPU HAL/runtime shim
```
