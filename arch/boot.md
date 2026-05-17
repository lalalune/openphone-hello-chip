# Boot flow

## Hello chip

The hello chip boot ROM is an identity ROM used by simulation and synthesis checks:

```text
0x0000_0000 = "OPSO"
0x0000_0004 = "CHIP"
0x0000_0008 = contract version 1
0x0000_000C = boot vector placeholder
```

No CPU is integrated in the hello chip. Testbenches act as the bus master.

## Full SoC target

```text
reset
management core starts from ROM
clock/reset controller releases application CPU
OpenSBI runs in M-mode
U-Boot loads kernel, initramfs, and device tree
Linux boots with serial console
Android userspace boots on the same hardware contract
```
