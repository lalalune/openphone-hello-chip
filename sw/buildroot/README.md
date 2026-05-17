# Buildroot target

Buildroot is the first full Linux userspace target before Android. It must consume `sw/platform/hello_platform_contract.json` or generated headers from it for hello MMIO base addresses and register offsets.

`make buildroot-check` rejects a documentation-only target. The check expects the first real target to provide:

```text
sw/buildroot/external.desc
sw/buildroot/Config.in
sw/buildroot/external.mk
sw/buildroot/scripts/import-buildroot-external.sh
sw/buildroot/configs/openphone_hello_defconfig
sw/buildroot/board/openphone/hello/linux.fragment
sw/buildroot/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke
serial console
initramfs
hello NPU userspace test
framebuffer smoke test
DMA smoke test
```

The Linux fragment also enables the kernel symbols needed for the external
SDIO `brcmfmac` WiFi and UART `hci_uart_bcm` Bluetooth reference slice. Those
symbols are BSP preparation only; the checked-in DTS keeps the module disabled
until board RTL and pin constraints provide the required host interfaces.

## Repo-local scaffold check

Command:

```sh
make buildroot-check
python3 sw/check_bsp_scaffolds.py buildroot
```

Expected output:

```text
buildroot BSP check passed.
buildroot: scaffold audit
  local command: make buildroot-check
  expected output: buildroot BSP check passed.
  dependency blocker: external Buildroot checkout and external Linux kernel tarball/tree
  status: clear
```

Dependency blocker: a real Buildroot image requires an external Buildroot
checkout and a kernel source/tarball that already contains the imported
OpenPhone Linux BSP. The checked-in `BR2_EXTERNAL` tree does not download
Buildroot or provide `../linux-external.tar.xz`.

## External Buildroot import

Use this directory as a `BR2_EXTERNAL` tree from an existing Buildroot checkout:

```sh
sw/buildroot/scripts/import-buildroot-external.sh /path/to/buildroot
cd /path/to/buildroot
make BR2_EXTERNAL=/path/to/OpenPhone-AI-SoC/sw/buildroot openphone_hello_defconfig
make BR2_EXTERNAL=/path/to/OpenPhone-AI-SoC/sw/buildroot
```

The helper only validates paths and prints deterministic commands. It does not
download Buildroot, fetch a kernel tarball, or start a full build.

Expected helper output starts with:

```text
Run from the Buildroot checkout:
  make BR2_EXTERNAL=/path/to/OpenPhone-AI-SoC/sw/buildroot openphone_hello_defconfig
```
