# NPU command ABI

The hello NPU command is intentionally trivial:

```text
write OP_A
write OP_B
write CTRL_STATUS.start
poll or wait for irq_npu
read RESULT
```

The full v0.1 NPU ABI should extend the same pattern:

```text
MMIO control registers
command queue
DMA descriptors
scratchpad allocation
INT8/INT4 GEMM commands
completion interrupt
performance counters
```
