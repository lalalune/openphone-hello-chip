# Android/Linux/BSP critical gap audit - 2026-05-17

Scope: `sw/**`, `docs/arch/android-contract.md`, `docs/android/riscv-bringup.md`,
`scripts/check_software_bsp.py`, `sw/check_bsp_scaffolds.py`, and the AOSP
product files under `sw/aosp-device/device/openphone/openphone_ai_soc`.

## Executive status

The repository contains useful Android/Linux/Buildroot scaffolds, but no
checked-in evidence that any Linux, Buildroot, AOSP, Cuttlefish, QEMU, or Renode
image has booted with this BSP. Treat all software BSP status as BLOCKED until
the required external-tree logs and boot transcripts are committed.

`sw/check_bsp_scaffolds.py` remains a source-presence audit. It can be clear
while the real BSP is blocked. `scripts/check_software_bsp.py` is the gate that
must stay BLOCKED until schema-listed evidence exists and passes transcript
marker validation.

## Placeholders and scaffolds

| Area | Checked-in state | Gap |
|---|---|---|
| Platform contract | `sw/platform/hello_platform_contract.json` still has `hello_chip.has_cpu=false` and `boot_vector_placeholder`. | No CPU-capable hello-chip boot target exists. |
| OpenSBI | `docs/sw/opensbi/README.md` is documentation-only. | No platform code, `fw_dynamic` handoff, RAM map, UART, timer, or interrupt proof. |
| U-Boot | `docs/sw/u-boot/README.md` is documentation-only. | No board port, defconfig, SPL/U-Boot image, boot media, or device-tree handoff. |
| Buildroot | `sw/buildroot` is a `BR2_EXTERNAL` skeleton with defconfig, fragment, and rootfs smoke script. | No external Buildroot checkout, no `linux-external.tar.xz`, no kernel/rootfs image, no runtime log. |
| Linux | `sw/linux` has importable NPU/DMA driver sources and DTS. | No external kernel checkout integration, no compiled modules, no DTB build, no boot log, no `/dev/hello-npu` smoke. |
| AOSP | `sw/aosp-device` has product, BoardConfig, device makefile, init, VINTF, fstab, sepolicy, kernel fragment, and DTS scaffolds. | No external AOSP checkout build, no `vendor.img`, no VINTF result, no Android boot transcript. |
| Android compatibility | `sw/aosp-device/evidence_manifest.json` lists bounded CTS/VTS subset evidence requirements. | No CTS, VTS, or CDD compatibility logs are checked in; no Android compatibility claim is allowed. |
| WiFi/Bluetooth | Linux DTS has disabled SDIO/UART nodes for a Murata/CYW4343W-class shape. | No SDIO host, UART, GPIO/pinctrl, power sequencing, RF path, firmware loading, or runtime evidence. |

## HAL stubs and Android gaps

| HAL/surface | File evidence | Gap to close |
|---|---|---|
| NPU HAL | `device.mk` declares `hello_npu.default`; `manifest.xml` declares `vendor.openphone.hello_npu@1.0`; init starts it only when `vendor.hello_npu.ready=1`. | No HAL source or binary exists in this repo or an external tree; no HIDL/AIDL interface source, VTS result, or fail-closed runtime test is checked in. |
| Graphics composer | `device.mk` declares `android.hardware.graphics.composer@2.4-service` and `hwcomposer.openphone_ai_soc`; `manifest.xml` declares composer 2.4. | No `hwcomposer.openphone_ai_soc` binary/source, no framebuffer or DRM node proof, no SurfaceFlinger log, no home-screen evidence. |
| Input | Runbook allows Cuttlefish/evdev only. | No hello_soc touch/input DTS, driver, HAL policy, or CTS input evidence. |
| Audio/camera/radio/GNSS/NFC | Explicitly excluded in docs. | No manifest entries or implementation; must remain excluded from claims. |
| SELinux | `file_contexts` and `hello_npu.te` label the NPU path and HAL domain. | Policy has not been compiled in AOSP, no `checkpolicy`/Soong output, no `avc` log review. |
| Fstab/storage | `fstab.openphone` names vendor and userdata by partition name. | No partition table, boot/vendor/userdata images, AVB chain, or mount log. |

## Missing external trees and images

Required but absent:

- External Linux tree with `drivers/misc/openphone-hello` imported.
- External Buildroot checkout using `sw/buildroot` as `BR2_EXTERNAL`.
- External AOSP checkout with `device/openphone/openphone_ai_soc` imported.
- Cuttlefish host setup with KVM, `launch_cvd`, `adb`, and riscv64 product.
- HAL implementation tree for `hello_npu.default`.
- HAL implementation tree for `hwcomposer.openphone_ai_soc`.
- Built Linux `Image`, DTB, modules, and boot log.
- Built Buildroot rootfs/kernel image and `hello-mmio-smoke` transcript.
- Built AOSP `vendor.img`, installed-files manifest, VINTF output, and boot log.

## Boot and simulator evidence gaps

| Target | Current evidence | Required evidence before PASS |
|---|---|---|
| AOSP Cuttlefish riscv64 | Runbook only. | `docs/evidence/android/cuttlefish_riscv64_boot.log` with `adb shell`, `ro.product.cpu.abi=riscv64`, and shell or `sys.boot_completed=1` proof. |
| OpenPhone AOSP product | Product files only. | `openphone_ai_soc_lunch.log`, `openphone_ai_soc_vendorimage.log`, `openphone_ai_soc_checkvintf.log`, and installed-files evidence. |
| Android compatibility subset | Manifest only. | `cts_virtual_device_subset.log` and `vts_virtual_device_subset.log` from real Tradefed commands; these are still not full CDD/CTS/VTS certification. |
| QEMU virt | Semantic qemu-virt checks and optional smoke path exist, but qemu-virt is not hello-chip ABI proof. | Bounded QEMU UART transcript for software reference, plus separate hello-chip MMIO proof before hardware claims. |
| Renode | Reference platform/check path only; docs state executable smoke is blocked without transcript. | Renode serial transcript loading the real firmware ELF and capturing the expected banner. |
| hello_soc RTL/Linux | No CPU-capable hello_soc boot path. | CPU, RAM, UART, timer, interrupt controller, OpenSBI handoff, Linux boot log, and MMIO smoke. |

## Kernel driver gaps

Implemented as importable source only:

- `openphone,hello-npu` misc char driver reads `HELLO_NPU_RESULT_OFFSET`.
- `openphone,hello-dma` platform driver exports a sysfs contract string.

Still missing:

- Display driver or simple framebuffer/DRM/KMS implementation.
- Timer/clocksource driver tied to Linux boot.
- Interrupt controller integration and real IRQ resources in DTS.
- GPIO/pinctrl driver.
- SDIO host driver path for WiFi.
- UART Bluetooth transport integration.
- DMA functional operations beyond a contract sysfs node.
- NPU ioctl/runtime ABI, fixed-vector execution path, and negative tests.
- Device-tree binding schemas and `dtbs_check` evidence.
- Module build logs, kernel config proof, boot logs, and userspace smoke logs.

## Machine-readable BLOCK gates

`scripts/check_software_bsp.py` now requires these evidence files through
`docs/evidence/software-bsp-evidence-manifest.json`:

| Target | Evidence files |
|---|---|
| Buildroot | `docs/evidence/buildroot/openphone_hello_defconfig.log`, `docs/evidence/buildroot/openphone_hello_image_manifest.txt`, `docs/evidence/buildroot/hello-mmio-smoke.log` |
| Linux | `docs/evidence/linux/openphone_hello_kernel_build.log`, `docs/evidence/linux/openphone_hello_dtb_check.log`, `docs/evidence/linux/hello-mmio-smoke.log` |
| OpenSBI | `docs/evidence/linux/opensbi_openphone_build.log`, `docs/evidence/linux/opensbi_fw_dynamic_handoff.log` |
| U-Boot | `docs/evidence/linux/u_boot_openphone_build.log`, `docs/evidence/linux/u_boot_opensbi_boot_chain.log` |
| AOSP / Android | `docs/evidence/android/openphone_ai_soc_lunch.log`, `docs/evidence/android/openphone_ai_soc_vendorimage.log`, `docs/evidence/android/openphone_ai_soc_checkvintf.log`, `docs/evidence/android/cuttlefish_riscv64_boot.log`, `docs/evidence/android/cts_virtual_device_subset.log`, `docs/evidence/android/vts_virtual_device_subset.log` |

Until those files exist with real command transcripts, `make software-bsp-check`
prints BLOCKED status and `make software-bsp-evidence-check` fails. Placeholder
logs, failed transcripts, templates, and files missing required command/pass
markers are rejected.

Capture entry points:

- Buildroot: `sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot defconfig|image-manifest|smoke`
- Linux: `sw/linux/scripts/capture-linux-bsp-evidence.sh /path/to/linux kernel-build|dtb-check|smoke`
- OpenSBI: `sw/opensbi/capture-opensbi-evidence.sh /path/to/opensbi build|handoff`
- U-Boot: `sw/u-boot/capture-u-boot-evidence.sh /path/to/u-boot build|boot-chain`
- AOSP: `sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp lunch|vendorimage|checkvintf|cuttlefish-boot|cts-subset|vts-subset`
