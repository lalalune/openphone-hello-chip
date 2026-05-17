# Chipyard generator slot

This directory is reserved for project-specific Chipyard configs after `scripts/bootstrap_chipyard.sh` populates `external/chipyard`.

First target:

```text
2x Rocket RV64GC
UART
timer/interrupts
RAM
hello NPU/display MMIO attachment points
Linux boot path
```

Generated Verilog should be copied or symlinked into `rtl/wrappers/` only through documented Make targets so RTL regressions remain reproducible.
