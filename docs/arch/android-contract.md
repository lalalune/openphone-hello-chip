# Android hardware contract

The hello chip does not boot Android. It establishes the minimal hardware contracts that will later back Linux drivers and AOSP HALs.

The central software-visible contract is `sw/platform/hello_platform_contract.json`. Android, Linux, and Buildroot scaffolding must consume that contract or generated artifacts from it instead of copying register addresses into unchecked placeholders.

QEMU/Renode bring-up uses a separate qemu-virt software reference target. Passing on qemu-virt proves boot scaffolding and userspace plumbing only; it does not prove the hello-chip package debug/MMIO ABI.

| Android need | Hello chip representation | Full SoC direction |
| --- | --- | --- |
| Boot identity | Boot ROM contract version | ROM, fuses/OTP abstraction, boot policy |
| Timers | Timer compare IRQ | CLINT/ACLINT plus Linux clocksource |
| Interrupts | Dedicated IRQ pins | PLIC/IMSIC routing |
| Display | Framebuffer and vsync registers | DRM/KMS driver and simple HWC path |
| NPU | Command/status/result registers | Linux char/DRM accel driver plus runtime/HAL |
| Storage | DMA-style command pattern | SD/eMMC controller first |
| GPIO/sensors | GPIO and I2C-oriented placeholder | GPIO, I2C sensor hub, input events |

The first AOSP target should live under `sw/aosp-device/device/openphone/openphone_ai_soc` and boot on QEMU/Renode before RTL simulation is expected to run Android-scale workloads. `make aosp-bsp-check` intentionally fails until that target contains real BoardConfig, init, manifest, SELinux, HAL plumbing tied back to the central contract, and checked-in external build/boot evidence.
