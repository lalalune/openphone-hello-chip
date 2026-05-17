# CTS / VTS Smoke Plan (Cuttlefish riscv64)

This plan picks the subset of CTS and VTS modules that can run against the
pre-silicon Cuttlefish riscv64 virtual device. It excludes anything that
requires camera, cellular, audio, Vulkan, GLES conformance, biometrics, secure
element, Widevine L1, Play services, or GMS — none of those exist on this
target.

A passing run of this subset is **not** Android CDD compatibility. It is the
smallest set that proves the userspace, kernel, binder, VINTF, and SELinux
plumbing is alive end-to-end on riscv64. CDD compatibility requires hardware
the simulator does not have.

## Prerequisites

- `docs/android/cuttlefish-riscv64-bringup.md` is green (shell-first boot
  succeeds and the boot-marker checklist is recorded).
- The AOSP tree at `~/aosp-riscv64` has built `cts` and `vts` host harnesses:
  ```sh
  source build/envsetup.sh
  lunch aosp_cf_riscv64_phone-trunk_staging-userdebug
  m -j"$(nproc)" cts vts
  ```
- `cts-tradefed` and `vts-tradefed` are on `PATH`:
  - `out/host/linux-x86/cts/android-cts/tools/cts-tradefed`
  - `out/host/linux-x86/vts/android-vts/tools/vts-tradefed`
- A single Cuttlefish device is reachable: `adb devices` lists exactly one
  `device` (not `offline`, not `unauthorized`).
- Archive root: `out/cf-riscv64/cts-vts/<UTC timestamp>/`.

## Module Selection Principles

Include a module only if all are true:
1. It exercises kernel, libc, binder, VINTF, SELinux, or framework plumbing.
2. It does not require camera, cellular/telephony, audio HAL, Vulkan, GLES,
   biometrics, secure element, NFC, GPS, Play services, or Widevine.
3. It does not require an instrumented activity manager configuration the
   Cuttlefish riscv64 image does not ship.

## CTS Smoke Modules

| Module | What it proves | Why safe on cf-riscv64 |
|---|---|---|
| `CtsLibcoreTestCases` | OpenJDK / libcore correctness on riscv64 | CPU + libc + ART; no peripherals. |
| `CtsLibcoreOjTestCases` | OpenJDK OJ subset | Same as above. |
| `CtsBionicTestCases` | Bionic libc + linker on riscv64 | CPU + libc; no peripherals. |
| `CtsNetTestCases` (lite filter, see below) | Sockets, DNS, basic IPv4/IPv6 | Cuttlefish provides a virtual NIC. |
| `CtsSecurityTestCases` (subset, see below) | SELinux policy, file modes, ASLR | Userspace-only checks. |
| `CtsSelinuxTargetSdkCurrentTestCases` | SELinux target-SDK policy paths | Userspace-only. |
| `CtsAppOpsTestCases` | AppOps framework | Framework services only. |
| `CtsPermissionTestCases` | Runtime permission framework | Framework services only. |
| `CtsContentTestCases` (lite filter) | ContentResolver / providers | Framework services only. |
| `CtsOsTestCases` (lite filter) | Process, Looper, Handler, etc. | Framework services only. |
| `CtsJniTestCases` | JNI ABI on riscv64 | CPU + ART. |
| `CtsUtilTestCases` | `android.util` helpers | Pure framework. |

### CTS "lite" filter rules

- `CtsNetTestCases`: include `android.net.cts.SocketTest`,
  `android.net.cts.UriTest`, `android.net.cts.DnsTest`. Exclude tethering,
  Wi-Fi, cellular, VPN policy, IpSec, IKE.
- `CtsSecurityTestCases`: include `SELinux*`, `FileSystemPermissionTest`,
  `BannedFilesTest`. Exclude `MediaServerHostTests`, kernel-CVE poke tests that
  require unsupported syscalls or hardware.
- `CtsContentTestCases`: exclude `ClipboardManager*` UI flows and SyncAdapter
  tests that require account services.
- `CtsOsTestCases`: exclude `BatteryStats*`, `StrictMode` network flakes.

### CTS command

```sh
export ARCHIVE=out/cf-riscv64/cts-vts/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ARCHIVE"

cts-tradefed run commandAndExit cts \
  --abi riscv64 \
  --module CtsLibcoreTestCases \
  --module CtsBionicTestCases \
  --module CtsJniTestCases \
  --module CtsUtilTestCases \
  --module CtsAppOpsTestCases \
  --module CtsPermissionTestCases \
  --module CtsSelinuxTargetSdkCurrentTestCases \
  --module CtsSecurityTestCases \
    --include-filter "CtsSecurityTestCases android.security.cts.SELinuxTest" \
    --include-filter "CtsSecurityTestCases android.security.cts.FileSystemPermissionTest" \
  --module CtsNetTestCases \
    --include-filter "CtsNetTestCases android.net.cts.SocketTest" \
    --include-filter "CtsNetTestCases android.net.cts.UriTest" \
  --log-level-display info \
  --skip-preconditions \
  | tee "$ARCHIVE/cts-stdout.log"

cp -r "$(ls -td out/host/linux-x86/cts/android-cts/results/* | head -1)" \
  "$ARCHIVE/cts-results/"
```

### CTS pass criteria

For each module:
- Tradefed reports `PASSED` for every included test, OR every `FAILED` test is
  classified in `$ARCHIVE/cts-triage.md` as one of:
  `expected-exclusion`, `product-bug`, `infra-bug`, `unknown`.
- No SELinux denial in `adb logcat` is silently waived. Each denial must link
  to a sepolicy issue or a device-contract entry.
- `test_result.xml` and `device-info-files/` are archived under
  `$ARCHIVE/cts-results/`.

## VTS Smoke Modules

| Module | What it proves | Why safe on cf-riscv64 |
|---|---|---|
| `VtsKernelConfigTest` | Kernel `CONFIG_*` required by Android present | Static kernel check. |
| `VtsKernelProcFileApiTest` | `/proc` ABI present | Kernel ABI surface only. |
| `VtsTrebleVintfTest` | Vendor + framework manifests + matrices compatible | VINTF correctness. |
| `VtsBinderTest` | Binder driver alive | Kernel + libbinder only. |
| `VtsHalManagerTest` | `hwservicemanager`/`servicemanager` healthy | Service manager only. |
| `VtsHalTest` (declared HALs only) | All HALs in the vendor manifest answer their interface descriptors | Limited to whatever the cf-riscv64 vendor.img declares. Skip any HAL not listed. |
| `VtsSecuritySELinuxPolicyHostTest` | Vendor sepolicy parses + matches expected types | Host-side parse. |

Skip explicitly:
- `VtsHalGraphicsComposer*` (no display HAL claim on cf-riscv64 GPU path)
- `VtsHalCamera*`, `VtsHalAudio*`, `VtsHalNeuralnetworks*` (no claim yet)
- `VtsHalBiometrics*`, `VtsHalKeymint*` strongbox variants (no SE)
- `VtsHalRadio*`, `VtsHalCellBroadcast*`, `VtsHalSim*`

### VTS command

```sh
export ARCHIVE=out/cf-riscv64/cts-vts/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$ARCHIVE"

vts-tradefed run commandAndExit vts \
  --module VtsKernelConfigTest \
  --module VtsKernelProcFileApiTest \
  --module VtsTrebleVintfTest \
  --module VtsBinderTest \
  --module VtsHalManagerTest \
  --module VtsSecuritySELinuxPolicyHostTest \
  --log-level-display info \
  --skip-preconditions \
  | tee "$ARCHIVE/vts-stdout.log"

cp -r "$(ls -td out/host/linux-x86/vts/android-vts/results/* | head -1)" \
  "$ARCHIVE/vts-results/"
```

### VTS pass criteria

- `VtsTrebleVintfTest`: every declared HAL in `vendor/etc/vintf/manifest.xml`
  is matched by the framework compatibility matrix the build shipped.
- `VtsKernelConfigTest`: zero `MISSING` lines for `requiredConfigs`. Optional
  configs may be missing if the cf-riscv64 kernel does not enable them; record
  the diff in `$ARCHIVE/vts-triage.md`.
- `VtsHalManagerTest`: every advertised service is reachable.
- `test_result.xml` is archived.

## Archive Layout

```
out/cf-riscv64/cts-vts/<UTC>/
  build-info.txt          # AOSP BUILD_ID, manifest sha256, host info
  device-info.txt         # adb getprop dump
  cts-stdout.log
  cts-results/            # tradefed xml + html + device-info
  cts-triage.md           # any non-pass: expected/product/infra/unknown
  vts-stdout.log
  vts-results/
  vts-triage.md
```

`build-info.txt` is the join key between the boot recipe and this run. It must
include the same `BUILD_ID` and manifest sha256 captured in
`docs/android/cuttlefish-riscv64-bringup.md`.

## Wrappers

`scripts/android/run_cts_smoke.sh` and `scripts/android/run_vts_smoke.sh` are
the canonical entry points. They fail closed if:
- `AOSP_TREE` is unset or does not point at a built AOSP riscv64 tree.
- `adb devices` does not list exactly one ready device.
- `cts-tradefed` / `vts-tradefed` is not on `PATH`.

This plan exists to be executed by those wrappers, not by hand.

## References

- Android CTS: https://source.android.com/docs/compatibility/cts
- Android VTS: https://source.android.com/docs/core/tests/vts
- Treble VINTF: https://source.android.com/docs/core/architecture/vintf
- SELinux on Android: https://source.android.com/docs/security/features/selinux
