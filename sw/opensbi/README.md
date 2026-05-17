# OpenSBI port scaffold

The full SoC target should boot through OpenSBI before U-Boot and Linux.

The hello chip currently has no CPU. OpenSBI integration starts once the
Chipyard/Rocket subsystem exists and `sw/platform/hello_platform_contract.json`
has RAM, UART, timer, interrupt-controller, and boot-handoff entries for a
CPU-capable target.

Repo-local command:

```sh
make software-bsp-check
python3 sw/check_bsp_scaffolds.py boot
```

Expected output:

```text
buildroot BSP check failed:
  - buildroot BSP BLOCKED: missing evidence for external Buildroot image build plus hello MMIO smoke transcript: docs/evidence/buildroot/openphone_hello_defconfig.log, docs/evidence/buildroot/openphone_hello_image_manifest.txt, docs/evidence/buildroot/hello-mmio-smoke.log
linux BSP check failed:
  - linux BSP BLOCKED: missing evidence for external Linux kernel build, DTB validation, and runtime driver smoke transcript: docs/evidence/linux/openphone_hello_kernel_build.log, docs/evidence/linux/openphone_hello_dtb_check.log, docs/evidence/linux/hello-mmio-smoke.log
aosp BSP check failed:
  - aosp BSP BLOCKED: missing evidence for external AOSP lunch/vendorimage/VINTF logs plus Cuttlefish or equivalent boot transcript: docs/evidence/android/openphone_ai_soc_lunch.log, docs/evidence/android/openphone_ai_soc_vendorimage.log, docs/evidence/android/openphone_ai_soc_checkvintf.log, docs/evidence/android/cuttlefish_riscv64_boot.log
boot: scaffold audit
  local command: make software-bsp-check
  expected output: buildroot BSP check passed.; linux BSP check passed.; aosp BSP check passed.
  dependency blocker: CPU-capable SoC integration with RAM, UART, timer, interrupt controller, OpenSBI handoff
  status: clear
```

Dependency blocker: a real OpenSBI build requires a CPU-capable SoC integration
with reset vector, RAM, UART, timer, interrupt controller, and a selected
OpenSBI platform or generic `fw_dynamic` handoff. Until then this directory is
documentation-only and must not be treated as boot evidence.
