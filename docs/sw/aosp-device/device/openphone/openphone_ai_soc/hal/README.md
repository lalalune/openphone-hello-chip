# OpenPhone AOSP HAL plan

This directory is intentionally documentation-only in the repo-local scaffold.
Do not add `hello_npu.default`, `hwcomposer.openphone_ai_soc`, or active VINTF
HAL entries until an external AOSP tree has buildable source or reviewed
prebuilts and archived evidence logs.

Required fail-closed behavior:

- `hello_npu.default`: open `/dev/hello-npu`; if absent, report unsupported and
  do not claim accelerator availability. When present, allow only a fixed-vector
  smoke path backed by the Linux driver and platform contract.
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
