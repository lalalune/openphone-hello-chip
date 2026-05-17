# OpenPhone-AI-SoC v0.1 architecture contract

The first executable artifact is `hello_soc`, a tiny pre-tapeout chip used to validate the repository, toolchain, and verification flow.

## Hello chip blocks

```text
boot ROM
MMIO peripheral block
timer interrupt
GPIO output
DMA command stub
NPU command stub
display controller stub
```

## Full SoC target

The long-term target remains an AOSP-capable open RISC-V AI phone application processor:

```text
RV64GC application CPU subsystem
management/security RISC-V core
cache hierarchy
TileLink/AXI interconnect
external memory controller/PHY boundary
on-chip SRAM
NPU
DMA
display and 2D graphics
storage, USB digital boundary, audio, sensors, GPIO, debug
OpenSBI, U-Boot, Linux, AOSP device support
```

The hello chip keeps the same contract style while making the first end-to-end flow fast enough to run constantly.
