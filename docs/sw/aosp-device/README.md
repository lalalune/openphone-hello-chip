# AOSP device target

Repo-local source path:

```text
sw/aosp-device/device/openphone/openphone_ai_soc
```

External AOSP checkout path:

```text
device/openphone/openphone_ai_soc
```

Initial Android bring-up should target AOSP riscv64 Cuttlefish plus QEMU/Renode
before RTL simulation, but qemu-virt or Cuttlefish success is not hardware ABI
validation. Device and HAL code must tie back to
`sw/platform/hello_platform_contract.json` or generated artifacts from it.

Current local status: this repository has not verified Android booting on
hello_soc or on Cuttlefish. The files here are an executable scaffold for the
first external AOSP integration attempt.

`make aosp-bsp-check` rejects a documentation-only target. The initial Android bring-up target must provide:

```text
import-aosp-device.sh
capture-aosp-evidence.sh
manifests/openphone-ai-soc-local.xml
AndroidProducts.mk
openphone_ai_soc.mk
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
HAL scaffolds
framebuffer/display path
NPU HAL/runtime shim
```

## Repo-local scaffold check

Command:

```sh
make aosp-bsp-check
python3 sw/check_bsp_scaffolds.py aosp
```

Expected output:

```text
aosp: scaffold audit
  local command: make aosp-bsp-check
  expected output: aosp BSP check passed.
  dependency blocker: external AOSP checkout with riscv64/Cuttlefish host dependencies and HAL binaries
  status: clear
aosp BSP check passed.
aosp BSP external evidence blocked:
  - aosp BSP BLOCKED: evidence for external AOSP lunch/vendorimage/VINTF logs, Cuttlefish or equivalent boot transcript, and Android compatibility subset transcripts is incomplete or invalid
  - missing docs/evidence/android/openphone_ai_soc_lunch.log
  - missing docs/evidence/android/openphone_ai_soc_vendorimage.log
  - missing docs/evidence/android/openphone_ai_soc_checkvintf.log
  - missing docs/evidence/android/cuttlefish_riscv64_boot.log
  - missing docs/evidence/android/cts_virtual_device_subset.log
  - missing docs/evidence/android/vts_virtual_device_subset.log
```

Dependency blocker: a real Android build requires an external AOSP checkout,
riscv64/Cuttlefish host dependencies, and actual `hello_npu.default` and
`hwcomposer.openphone_ai_soc` HAL source or reviewed prebuilts that fail closed
when their backing Linux nodes are absent. This repo includes a host-buildable
`hello_npu` runtime probe under `hal/` so the absent-device behavior is locally
checked; the checked-in `device.mk` and VINTF manifest intentionally do not
list active HAL packages or HAL entries until Android integration and evidence
exist.

Evidence intake is defined by
`docs/evidence/software-bsp-evidence-manifest.json` and validated by
`make software-bsp-evidence-check`. The checker rejects non-evidence stubs:
each transcript must include the `openphone-evidence` header/footer, command
marker, and target-specific pass markers.

## External AOSP integration

Use a Linux host with Cuttlefish/KVM enabled. From an AOSP checkout:

```sh
/path/to/OpenPhone-AI-SoC/sw/aosp-device/import-aosp-device.sh /path/to/aosp
cd /path/to/aosp
source build/envsetup.sh
lunch openphone_ai_soc-userdebug
m nothing
m vendorimage
```

The import helper copies only the device tree into an existing AOSP checkout.
It does not run `repo sync`, download AOSP, or build Android.

The single-command driver for this flow is:

```sh
AOSP_DIR=/path/to/aosp make android-sim-boot-check
```

That target imports the device tree, captures `lunch`, `vendorimage`, and
`checkvintf` evidence, then validates the AOSP evidence manifest. To attempt a
Cuttlefish boot as well:

```sh
AOSP_DIR=/path/to/aosp scripts/boot_android_simulator.sh --run-cuttlefish
```

`--run-cuttlefish` requires a Linux AOSP environment with Cuttlefish tools on
`PATH`. On hosts without `launch_cvd`/`cvd`, the script writes
`build/reports/android_sim_boot.json` with `status=blocked` instead of treating
missing simulator support as an Android boot failure.

Android compatibility remains blocked separately from AOSP build and boot.
`sw/aosp-device/evidence_manifest.json` requires bounded CTS and VTS
virtual-device subset transcripts before any compatibility language is allowed;
those logs are not full CDD, CTS, or VTS certification evidence.

Capture external logs with the repo helper so the strict evidence gate sees the
required provenance markers:

```sh
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp lunch
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vendorimage
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp checkvintf
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cuttlefish-boot
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cts-subset
/path/to/OpenPhone-AI-SoC/sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vts-subset
```

These commands write under `docs/evidence/android/`. They capture command
transcripts only; they do not make a boot claim unless the external log contains
real Cuttlefish/adb output and passes `make software-bsp-evidence-check`. The
CTS/VTS modes are bounded virtual-device subset captures, not CDD, GMS, or full
Android compatibility evidence.

The Cuttlefish boot capture defaults to `AOSP_PRODUCT=openphone_ai_soc-userdebug`
and `AOSP_CUTTLEFISH_ARGS="--cpus=4 --memory_mb=8192 --gpu_mode=none"`.
Override those environment variables when running a different riscv64
Cuttlefish product or a home-screen launch.

Required Android boot-evidence inputs are intentionally explicit:

| Evidence log | External artifact or marker that must back it |
|---|---|
| `docs/evidence/android/openphone_ai_soc_lunch.log` | `build/envsetup.sh`, `device/openphone/openphone_ai_soc/AndroidProducts.mk`, `TARGET_PRODUCT=openphone_ai_soc` |
| `docs/evidence/android/openphone_ai_soc_vendorimage.log` | `out/target/product/openphone_ai_soc/vendor.img`, `out/target/product/openphone_ai_soc/installed-files-vendor.txt`, `out/target/product/openphone_ai_soc/vendor/etc/vintf/manifest/openphone_hello.xml` |
| `docs/evidence/android/openphone_ai_soc_checkvintf.log` | `checkvintf` output against `out/target/product/openphone_ai_soc/vendor` and `openphone_hello.xml` |
| `docs/evidence/android/cuttlefish_riscv64_boot.log` | `launch_cvd`, `adb shell`, `ro.product.cpu.abi=riscv64`, and `sys.boot_completed=1` |
| `docs/evidence/android/cts_virtual_device_subset.log` | `cts-tradefed` virtual-device subset result directory |
| `docs/evidence/android/vts_virtual_device_subset.log` | `vts-tradefed` virtual-device subset result directory |

The Cuttlefish capture no longer accepts shell-only smoke as boot evidence:
`sys.boot_completed=1` is required for a PASS transcript.

`manifests/openphone-ai-soc-local.xml` is a local-manifest starting point for
teams that mirror this repository into an AOSP `repo` workspace. The script
above is the deterministic path for a plain local checkout.

Expected first-pass artifacts:

```text
out/target/product/openphone_ai_soc/vendor.img
out/target/product/openphone_ai_soc/installed-files-vendor.txt
out/target/product/openphone_ai_soc/obj/PACKAGING/check_vintf_all_intermediates/
```

If `lunch openphone_ai_soc-userdebug` is not visible, add the product makefile
to the external tree's product list before changing the board files. If
`vendorimage` fails, classify the failure as missing HAL binary, VINTF mismatch,
SELinux type error, missing kernel/DTS artifact, or generic AOSP product wiring.

## External evidence capture

From this repository, with `/path/to/aosp` already provisioned:

```sh
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp lunch
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vendorimage
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp checkvintf
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cuttlefish-boot
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cts-subset
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vts-subset
make software-bsp-evidence-check
```

The Cuttlefish capture requires `ro.product.cpu.abi=riscv64` and
`sys.boot_completed=1`. It is Android userspace evidence only; it is not
hello_soc hardware ABI proof. The CTS/VTS
captures are virtual-device subsets only and must not be described as full
Android compatibility evidence.

## Artifact map

| Artifact | Repo file | Purpose |
|---|---|---|
| Import helper | `import-aosp-device.sh` | Copies device files into an external AOSP checkout and prints lunch checks. |
| Evidence capture helper | `capture-aosp-evidence.sh` | Captures external AOSP command transcripts with required evidence markers. |
| Local manifest seed | `manifests/openphone-ai-soc-local.xml` | Records the intended repo workspace path for mirrored integrations. |
| Product list | `device/openphone/openphone_ai_soc/AndroidProducts.mk` | Exposes `openphone_ai_soc-userdebug` to `lunch`. |
| Lunch product | `device/openphone/openphone_ai_soc/openphone_ai_soc.mk` | Inherits generic AOSP product glue and the OpenPhone device makefile. |
| Board config | `device/openphone/openphone_ai_soc/BoardConfig.mk` | Declares riscv64 target and vendor policy directories. |
| Product makefile | `device/openphone/openphone_ai_soc/device.mk` | Copies init, fstab, and the empty VINTF scaffold; HAL packages stay disabled until evidence exists. |
| Init | `device/openphone/openphone_ai_soc/init.openphone.rc` | Creates the hello device namespace and starts the NPU HAL only when enabled. |
| Fstab | `device/openphone/openphone_ai_soc/fstab.openphone` | Documents first vendor/data mount contract for simulator integration. |
| VINTF manifest | `device/openphone/openphone_ai_soc/manifest.xml` | Reserves graphics-composer and hello_npu names in comments only. |
| SELinux contexts | `device/openphone/openphone_ai_soc/sepolicy/file_contexts` | Labels HAL binaries and `/dev/hello-npu`. |
| SELinux types | `device/openphone/openphone_ai_soc/sepolicy/hello_npu.te` | Defines the fail-closed NPU device and HAL domains. |
| Kernel fragment | `device/openphone/openphone_ai_soc/kernel/openphone_ai_soc.fragment` | Records Android kernel config needed by the scaffold. |
| DTS scaffold | `device/openphone/openphone_ai_soc/dts/openphone-hello-android.dts` | Mirrors the central platform contract for Android-facing nodes. |
| HAL runtime skeleton | `device/openphone/openphone_ai_soc/hal/hello_npu_runtime.cc` | Host-buildable fail-closed probe for absent `/dev/hello-npu`; always reports `nnapi_acceleration=false` in local checks. |
| HAL probe CLI | `device/openphone/openphone_ai_soc/hal/hello_npu_probe_main.cc` | CLI used by `sw/check_bsp_scaffolds.py aosp` to verify absent-device behavior without fake device evidence. |
| HAL plan | `device/openphone/openphone_ai_soc/hal/README.md` | Defines fail-closed behavior required before package claims are enabled. |

## HAL stub policy

Stubs must not claim feature success unless backed by a Linux node or the
central platform contract.

| HAL/package | Backing node | Required v0 behavior |
|---|---|---|
| `hello_npu.default` | `/dev/hello-npu` | Return unsupported when the device node is absent; only fixed-vector smoke is allowed when present. |
| `hwcomposer.openphone_ai_soc` | framebuffer/display node | Expose a simple framebuffer path only; no GLES or Vulkan claim. |
| input | Cuttlefish/evdev only | No touch-panel claim for hello_soc. |
| camera/audio/radio/GNSS/NFC | none | No package, no VINTF entry, no CTS claim. |

## Local checks

Run from the repository root:

```sh
make aosp-bsp-check
make docs-check
```

`docs-check` does not currently inspect this AOSP tree directly, so
`aosp-bsp-check` is the primary local guard for this ownership area. It must
remain BLOCKED until external AOSP build and boot evidence is checked in.
