# Buildroot target

Buildroot is the first full Linux userspace target before Android. It must consume `sw/platform/hello_platform_contract.json` or generated headers from it for hello MMIO base addresses and register offsets.

`make buildroot-check` rejects a documentation-only target. The check expects the first real target to provide:

```text
sw/buildroot/configs/openphone_hello_defconfig
sw/buildroot/board/openphone/hello/linux.fragment
sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke
serial console
initramfs
hello NPU userspace test
framebuffer smoke test
DMA smoke test
```
