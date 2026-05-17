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
buildroot: scaffold audit
  local command: make buildroot-check
  expected output: buildroot BSP check passed.
  dependency blocker: external Buildroot checkout and external Linux kernel tarball/tree
  status: clear
buildroot BSP check failed:
  - buildroot BSP BLOCKED: missing evidence for external Buildroot image build plus hello MMIO smoke transcript: docs/evidence/buildroot/openphone_hello_defconfig.log, docs/evidence/buildroot/openphone_hello_image_manifest.txt, docs/evidence/buildroot/hello-mmio-smoke.log
```

Dependency blocker: a real Buildroot image requires an external Buildroot
checkout and a kernel source/tarball that already contains the imported
OpenPhone Linux BSP. The checked-in `BR2_EXTERNAL` tree does not download
Buildroot or provide `../linux-external.tar.xz`.

Evidence intake is defined by
`docs/evidence/software-bsp-evidence-manifest.json` and validated by
`make software-bsp-evidence-check`. A file existing under `docs/evidence` is
not enough: the transcript must include the `openphone-evidence` header/footer,
the exact command marker, and the target-specific pass markers. Templates,
substitute-only logs, failed transcripts, and too-small files are rejected.

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

## External evidence capture

From this repository, with `/path/to/buildroot` already provisioned:

```sh
sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot defconfig
sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot image-manifest
HELLO_SMOKE_CMD='ssh root@TARGET /usr/bin/hello-mmio-smoke' \
  sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot smoke
make software-bsp-evidence-check
```

The `image-manifest` mode records SHA-256 hashes for files already present in
`output/images`; it fails if no image build exists. The `smoke` mode fails
unless `HELLO_SMOKE_CMD` exits zero on the external target.
