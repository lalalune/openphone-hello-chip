# Linux BSP

Linux BSP artifacts must consume `sw/platform/hello_platform_contract.json` or generated headers from it for hello MMIO base addresses, IRQ names, and register offsets.

`make linux-bsp-check` rejects a documentation-only BSP. The first Linux-facing artifacts are:

```text
sw/linux/dts/openphone-hello.dts
sw/linux/drivers/hello/hello-npu.c
sw/linux/drivers/hello/hello-dma.c
sw/linux/tests/hello-mmio-smoke.c
device tree binding for hello MMIO blocks
timer/GPIO smoke driver
NPU char driver
simple framebuffer or DRM/KMS display driver
DMA test driver
```
