# Linux BSP

Linux BSP artifacts must consume `sw/platform/hello_platform_contract.json` or generated headers from it for hello MMIO base addresses, IRQ names, and register offsets.

`make linux-bsp-check` rejects a documentation-only BSP. The first Linux-facing artifacts are:

```text
sw/linux/drivers/hello/Kconfig
sw/linux/drivers/hello/Makefile
sw/linux/scripts/import-linux-bsp.sh
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

The WiFi/Bluetooth BSP slice is a disabled DTS scaffold for an external Murata Type
1DX / CYW4343W-class module shape. It names the intended SDIO `brcmfmac` WiFi
device, UART `hci_uart_bcm` Bluetooth transport, and power sequencing hook, but
does not claim an implemented hello-chip SDIO host, UART, GPIO, pinctrl, or RF
block.

## Repo-local scaffold check

Command:

```sh
make linux-bsp-check
python3 sw/check_bsp_scaffolds.py linux
```

Expected output:

```text
linux BSP check passed.
linux: scaffold audit
  local command: make linux-bsp-check
  expected output: linux BSP check passed.
  dependency blocker: external Linux kernel checkout plus integration of drivers/misc/openphone-hello
  status: clear
```

Dependency blocker: a real Linux boot/image check requires an external kernel
checkout with `sw/linux/drivers/hello` imported under
`drivers/misc/openphone-hello`, `sw/linux/dts/openphone-hello.dts` copied into
`arch/riscv/boot/dts/openphone`, and board-owned Kconfig/Makefile fragments
that select `CONFIG_OPENPHONE_HELLO_NPU` and `CONFIG_OPENPHONE_HELLO_DMA`.

## External Linux import

The checked-in driver directory is ready to copy into an external Linux tree:

```sh
sw/linux/scripts/import-linux-bsp.sh /path/to/linux
mkdir -p /path/to/linux/drivers/misc/openphone-hello
rsync -a sw/linux/drivers/hello/ /path/to/linux/drivers/misc/openphone-hello/
cp sw/linux/dts/openphone-hello.dts /path/to/linux/arch/riscv/boot/dts/openphone/
```

Then add these external-tree fragments:

```make
# drivers/misc/Makefile
obj-$(CONFIG_OPENPHONE_HELLO_BSP) += openphone-hello/
```

```text
# drivers/misc/Kconfig
source "drivers/misc/openphone-hello/Kconfig"
```

The repo-local helper validates that the destination looks like a kernel tree
and prints the import commands. It does not patch or build the external kernel.

Expected helper output starts with:

```text
Import commands:
  mkdir -p /path/to/linux/drivers/misc/openphone-hello ...
```
