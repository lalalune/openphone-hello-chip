# OpenPhone AOSP HAL plan

This directory contains a host-buildable runtime skeleton for the future
`hello_npu.default` integration. Do not add `hello_npu.default`,
`hwcomposer.openphone_ai_soc`, or active VINTF HAL entries to the product until
an external AOSP tree has buildable source or reviewed prebuilts and archived
evidence logs.

Local fail-closed proof:

```sh
c++ -std=c++17 -Wall -Wextra -Werror \
  sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu_runtime.cc \
  sw/aosp-device/device/openphone/openphone_ai_soc/hal/hello_npu_probe_main.cc \
  -I sw/aosp-device/device/openphone/openphone_ai_soc/hal \
  -o /tmp/hello_npu_probe
/tmp/hello_npu_probe --device /tmp/definitely-missing-hello-npu
```

Required absent-device output includes:

```text
hello_npu_status=unsupported
device_node_present=false
runtime_supported=false
nnapi_acceleration=false
claim_boundary=no_nnapi_acceleration_without_android_nnapi_hal_and_device_evidence
```

`python3 sw/check_bsp_scaffolds.py aosp` builds and runs this probe with a
temporary missing path. That is local checker evidence only; it is not device
evidence and it does not prove Android NNAPI acceleration.

Required fail-closed behavior:

- `hello_npu.default`: open `/dev/hello-npu`; if absent, report unsupported and
  do not claim accelerator availability. When present, require a character
  device before any fixed-vector smoke path can run. The host runtime skeleton
  keeps `nnapi_acceleration=false` in all local-checker paths.
- `hwcomposer.openphone_ai_soc`: bind only to a proven framebuffer or DRM node.
  If no display node exists, fail service startup or report unsupported
  composition; do not claim GLES, Vulkan, camera, input, audio, radio, GNSS, or
  NFC support.

Evidence required before enabling packages:

- External `vendorimage` log showing the HAL binaries are built into
  `vendor.img`.
- External `checkvintf` log showing newly declared VINTF entries are compatible.
- SELinux policy and neverallow build logs.
- Bounded Cuttlefish, QEMU, or Renode smoke transcript that keeps Android boot
  claims separate from virtual-device smoke evidence.
# HAL Evidence Boundary

HAL source or prebuilts are not checked in. `hello_npu.default` and
`hwcomposer.openphone_ai_soc` remain blocked until external AOSP evidence exists.
