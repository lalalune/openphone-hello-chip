# Android RISC-V Bring-Up

The Android path is split into a simulator track and a physical-board track.
The simulator track proves that the software stack and device contracts are
coherent. The physical-board track proves that real drivers, clocks, memory,
display, and power behavior can survive Android workloads.

## Baseline Targets

| Target | Purpose | Status expectation |
|---|---|---|
| AOSP riscv64 / Cuttlefish | Fastest Android userspace and framework path | Use for simulator/home-screen work and app/runtime validation; not a proof of hello_soc hardware ABI. |
| QEMU virt | Kernel, init, shell, block, network, and device-contract smoke | Good for software plumbing; not hardware ABI proof. |
| Renode | Peripheral and firmware model smoke | Useful for deterministic device-model tests. |
| TH1520 board | Physical RISC-V Android baseline | Best purchasable Android/RISC-V reference, but not fully open SoC silicon. |
| hello_soc RTL | Open hardware contract proof | Tiny target; Linux/Android performance claims are non-v0. |

Current local evidence: Android has not been verified booting in this repo.
Treat the commands below as the required bring-up recipe and evidence checklist
until a checked-in transcript proves otherwise. The repo-local scaffold checks
are CLI-only and must not be reported as Android boot evidence.

## Host Prerequisites

Use a Linux host for Cuttlefish. The expected development host is Ubuntu or
Debian on x86_64 with hardware virtualization enabled.

Minimum host checks:

```sh
grep -c -w 'vmx\|svm' /proc/cpuinfo
find /dev -name kvm
groups "$USER" | grep -E 'kvm|cvdnetwork|render'
qemu-system-riscv64 --version
adb version
repo version
```

Expected results:

- `/dev/kvm` exists and the user is in `kvm`, `cvdnetwork`, and `render`.
- QEMU is at least 8.1; QEMU 9.0 or newer is preferred for vector-extension
  fixes.
- `repo`, `adb`, `launch_cvd`, and `stop_cvd` are in `PATH` after the AOSP
  environment is sourced.
- At least 250 GB free disk space and 32 GB RAM are available for a local AOSP
  build. A shell-only Cuttlefish run should use at least 8 GB guest RAM.

Cuttlefish host packages, when not provided by the OS image, are built and
installed from the Android Cuttlefish host package source:

```sh
sudo apt install -y git devscripts equivs config-package-dev \
  debhelper-compat golang curl
git clone https://github.com/google/android-cuttlefish
cd android-cuttlefish
tools/buildutils/build_packages.sh
sudo dpkg -i ./cuttlefish-base_*_*64.deb || sudo apt-get install -f
sudo dpkg -i ./cuttlefish-user_*_*64.deb || sudo apt-get install -f
sudo usermod -aG kvm,cvdnetwork,render "$USER"
sudo reboot
```

## AOSP riscv64 Cuttlefish Runbook

Use this track first because it exercises Android userspace, ART, framework
services, adb, and Tradefed without depending on the unfinished hello_soc CPU
and GPU story.

```sh
mkdir -p ~/aosp-riscv64
cd ~/aosp-riscv64
repo init -u https://android.googlesource.com/platform/manifest \
  -b android-latest-release
repo sync -c -j"$(nproc)"
source build/envsetup.sh
lunch aosp_cf_riscv64_phone-trunk_staging-userdebug
make -j"$(nproc)"
```

Shell-first launch:

```sh
launch_cvd -cpus=4 --memory_mb=8192 --gpu_mode=none --daemon
adb wait-for-device
adb shell getprop ro.product.cpu.abi
adb shell uname -m
adb shell logcat -d -b all > out/openphone-riscv64-logcat.txt
stop_cvd
```

Home-screen launch:

```sh
launch_cvd -cpus=8 --memory_mb=8192 --daemon
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell dumpsys SurfaceFlinger --display-id
adb shell logcat -d -b all > out/openphone-riscv64-home-logcat.txt
stop_cvd
```

Record failure as useful data. Do not update status to "Android running" unless
the transcript includes `adb shell`, `ro.product.cpu.abi=riscv64`, and either
`sys.boot_completed=1` or a clear shell-only success statement.

The checked-in capture wrapper records that bounded transcript shape without
fabricating pass markers:

```sh
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cuttlefish-boot
make software-bsp-evidence-check
```

For a different external Cuttlefish product or UI launch, set:

```sh
AOSP_PRODUCT=aosp_cf_riscv64_phone-trunk_staging-userdebug \
AOSP_CUTTLEFISH_ARGS="--cpus=8 --memory_mb=8192" \
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cuttlefish-boot
```

## OpenPhone AOSP Device Tree Runbook

The repo-local device tree is a scaffold intended to be copied or overlaid into
an external AOSP checkout:

```sh
cd ~/aosp-riscv64
mkdir -p device/openphone
rsync -a /path/to/OpenPhone-AI-SoC/sw/aosp-device/device/openphone/ \
  device/openphone/
source build/envsetup.sh
lunch openphone_ai_soc-userdebug
m nothing
m vendorimage
```

The first expected result is a useful build failure if a required Android
surface is not implemented. A successful `m vendorimage` only means the scaffold
is syntactically integrated; it does not mean Android boots on hello_soc.

Use the repo capture commands for archived evidence:

```sh
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp lunch
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vendorimage
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp checkvintf
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cts-subset
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vts-subset
```

The required evidence files, command markers, and pass markers are listed in
`docs/evidence/software-bsp-evidence-manifest.json`. The template under
`docs/evidence/templates/` is intentionally rejected by the checker.

Expected local artifacts after integration:

| Artifact | Producer | Evidence to attach |
|---|---|---|
| `out/target/product/openphone_ai_soc/vendor.img` | `m vendorimage` | `ls -lh`, build log, VINTF check result |
| `out/target/product/openphone_ai_soc/installed-files-vendor.txt` | AOSP build | HAL/init/fstab entries present |
| `out/target/product/openphone_ai_soc/obj/PACKAGING/vndk_intermediates` | AOSP build | VNDK/Treble packaging log |
| `out/openphone-riscv64-logcat.txt` | Cuttlefish run | boot, init, HAL, and SELinux evidence |
| `out/host/linux-x86/cts` | `m cts` | CTS subset invocation and result dir |
| `out/host/linux-x86/vts` | `m vts` | VTS subset invocation and result dir |

## v0 Device Contract

The `sw/aosp-device/device/openphone/openphone_ai_soc` tree must remain tied to
`sw/platform/hello_platform_contract.json`. Any HAL, init service, device-tree
node, or kernel driver added for Android must have a contract entry or an
explicit stub rationale.

The checked-in `sw/linux/dts/openphone-hello.dts` file is not a complete AP boot
DTB. For Android/Linux bring-up it must be combined with, or replaced by, the
selected generated AP DTS containing CPU, memory, timer, interrupt-controller,
and enabled UART console nodes. Run `python3 scripts/capture_cpu_ap_evidence.py
dts-audit --run-dtc` against the generated DTS before using it for OpenSBI,
Linux, or Android boot evidence.

Required v0 surfaces:

- boot image and kernel config contract
- serial console / log path
- framebuffer or stub display path
- input stub
- block storage path
- NPU service shim that can fail closed
- SELinux labels for project-owned device nodes
- init service declarations
- manifest entries for HAL stubs

## HAL Stub Map

All v0 HALs must either fail closed or delegate to the Linux device contract.
No stub may fake hardware success.

| Surface | AOSP artifact | Contract source | v0 behavior |
|---|---|---|---|
| Graphics composer | `hwcomposer.openphone_ai_soc` and VINTF `android.hardware.graphics.composer@2.4` | `display` MMIO region at `0x10030000` | Stub exposes a framebuffer path only after a Linux display node exists; otherwise service stays disabled or returns unsupported. |
| NPU | `hello_npu.default` and VINTF `vendor.openphone.hello_npu@1.0` | `npu` MMIO region at `0x10020000` and IRQ_NPU | Runtime shim runs fixed-vector smoke only when `/dev/hello-npu` exists; all other ops return unsupported. |
| DMA | No public Android HAL in v0 | `dma` MMIO region at `0x10010000` and IRQ_DMA | Kernel-only support for NPU/display staging; no framework exposure. |
| Input | Generic evdev or no-op input | Board DTS input node, when present | Simulator may use Cuttlefish input; hello_soc target has no touch claim. |
| Audio | None | No contract entry | Excluded; do not add manifest entries. |
| Camera | None | No contract entry | Excluded; do not add manifest entries. |
| Radio/modem | None | No contract entry | Excluded; do not add manifest entries. |
| Power/thermal | Minimal default Android services only | No power island contract yet | Excluded from performance claims. |

Explicit v0 exclusions:

- cellular modem integration
- carrier voice, VoLTE, VoNR, emergency calling
- GMS, Play certification, Widevine L1, HDCP
- full Vulkan/GLES performance path
- production camera HAL3
- full CTS/VTS pass

## Three-Week Android Target

The three-week target is not a consumer phone. It is a verified demo:

1. AOSP/riscv64 or Cuttlefish-based Android boots to shell or home screen.
2. The OpenPhone device tree and BoardConfig compile far enough to expose
   missing HAL/kernel contracts.
3. QEMU/Renode smoke checks pass against the platform contract.
4. The NPU runtime shim can run a deterministic fixed test vector or report
   unsupported operations without crashing Android.
5. CTS/VTS subsets are identified and at least the host-side plumbing exists.

## CTS/VTS Subset Plan

The first compatibility goal is a stable virtual-device subset, not a full
phone certification run.

Build test harnesses from the same AOSP checkout:

```sh
source build/envsetup.sh
lunch aosp_cf_riscv64_phone-trunk_staging-userdebug
m -j"$(nproc)" cts vts
```

Run order:

1. `adb shell true`, `adb shell cmd package list packages`, and
   `adb shell getenforce`.
2. CTS smoke modules that do not require camera, cellular, audio, Vulkan, GLES,
   biometrics, secure element, or Play services.
3. `cts-tradefed run cts-virtual-device-stable` when the riscv64 virtual device
   is stable enough to keep multiple shards online.
4. VTS kernel, VINTF, binder, SELinux, and HAL-manager checks for declared HALs.
5. Project-specific smoke: `/dev/hello-npu` absent must not crash Android;
   present must pass a fixed-vector runtime test before any NNAPI/TFLite claim.

Initial excludes:

- `CtsCameraTestCases`
- `CtsMedia*` modules requiring hardware codecs or microphones
- `CtsGraphics*` modules requiring GLES/Vulkan conformance
- telephony, eUICC, NFC, secure element, biometric, and GNSS modules
- NNAPI performance or accelerator conformance until the NPU HAL has a real
  framework integration

Pass criteria for the first report:

- test command line and AOSP build ID recorded
- result directory archived
- failed modules classified as expected exclusion, product bug, infra bug, or
  unknown
- no SELinux denial is waived without a linked policy or device-contract issue
- no CDD, full CTS, full VTS, or Android compatibility claim is made from these
  subset logs

## Failure Triage

Use this order so failures stay actionable:

| Symptom | First commands | Likely owner |
|---|---|---|
| Cuttlefish does not launch | `launch_cvd -verbosity=DEBUG`, `ls -l /dev/kvm`, `groups`, `cvd_status` | host setup |
| `adb devices` is empty | `adb kill-server; adb start-server`, `ss -ltnp | grep 652`, `tail -200 ~/cuttlefish_runtime/logs/*` | Cuttlefish/adb |
| riscv64 build fails before lunch | `repo branch`, `build/soong/soong_ui.bash --dumpvar-mode TARGET_ARCH` | AOSP branch/target |
| boot hangs before init | `tail -300 ~/cuttlefish_runtime/kernel.log`, `adb wait-for-device` | kernel/bootloader |
| init restarts HAL | `adb shell logcat -b all -d | grep -E 'init|hwservicemanager|hello|composer'` | device tree/HAL |
| VINTF failure | `adb shell lshal`, `adb shell vintf` when available, inspect vendor manifest | manifest/HAL |
| SELinux denial | `adb shell dmesg | grep avc`, `adb logcat -b all -d | grep avc` | sepolicy |
| UI never reaches home | `adb shell getprop sys.boot_completed`, `dumpsys SurfaceFlinger`, `logcat ActivityTaskManager` | graphics/framework |
| CTS module times out | `tradefed.sh list devices`, `adb logcat`, retry a single module | test infra or module |

## Evidence Required

Every Android bring-up report must include:

- AOSP branch or tag
- host OS and toolchain
- target architecture
- kernel config
- boot log
- init log
- SELinux denials
- HAL manifest state
- command transcript
- pass/fail status for `make aosp-bsp-check`
- pass/fail status for `python3 sw/check_bsp_scaffolds.py aosp`

Repo-local expected output before external AOSP work:

```text
aosp: scaffold audit
  local command: make aosp-bsp-check
  expected output: aosp BSP check passed.
  dependency blocker: external AOSP checkout with riscv64/Cuttlefish host dependencies and HAL binaries
  status: clear
aosp BSP check failed:
  - aosp BSP BLOCKED: evidence for external AOSP lunch/vendorimage/VINTF logs, Cuttlefish or equivalent boot transcript, and Android compatibility subset transcripts is incomplete or invalid
  - missing docs/evidence/android/openphone_ai_soc_lunch.log
  - missing docs/evidence/android/openphone_ai_soc_vendorimage.log
  - missing docs/evidence/android/openphone_ai_soc_checkvintf.log
  - missing docs/evidence/android/cuttlefish_riscv64_boot.log
  - missing docs/evidence/android/cts_virtual_device_subset.log
  - missing docs/evidence/android/vts_virtual_device_subset.log
```

Sources:

- AOSP RISC-V tracking: https://github.com/google/android-riscv64
- Android CTS: https://source.android.com/docs/compatibility/cts
- Android VTS: https://source.android.com/docs/core/tests/vts
- Android CDD: https://source.android.com/docs/compatibility/cdd
