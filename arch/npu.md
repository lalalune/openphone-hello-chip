# NPU command ABI

The hello NPU is a small synthesizable datapath behind a single-cycle MMIO
control interface. Software programs operands, selects an opcode, starts the
command, then polls `CTRL_STATUS.done` or waits for `irq_npu`.

```text
write OP_A
write OP_B
write ACC              ; optional, used by MAC/DOT4
write OPCODE
write CTRL_STATUS.start
poll or wait for irq_npu
read RESULT
```

`OPCODE` is read/write; readback returns the programmed low 4 bits. `RESULT_HI`
contains the high word for `MUL_LO` and sign-extension for signed 32-bit
`MAC_S16`/`DOT4_S8` results.

Implemented opcodes:

| Opcode | Name | Result |
| ---: | --- | --- |
| `0` | `ADD` | `OP_A + OP_B` |
| `1` | `SUB` | `OP_A - OP_B` |
| `2` | `MUL_LO` | low 32 bits of unsigned `OP_A * OP_B`; high word in `RESULT_HI` |
| `3` | `MAC_S16` | signed low-16 multiply plus signed `ACC` |
| `4` | `DOT4_S8` | four packed signed INT8 products plus signed `ACC` |
| `5` | `MAX_U32` | unsigned max |
| `6` | `MIN_U32` | unsigned min |

Status bits:

| Bit | Name | Meaning |
| ---: | --- | --- |
| `0` | `busy` | Command is executing |
| `1` | `done` | Command completed; also drives `irq_npu` |
| `2` | `error` | Unsupported opcode was rejected |

Write `CTRL_STATUS[1]` to clear `done` and `error`. Operands are latched when
`start` is accepted; software should not rely on mid-command register writes
affecting the in-flight operation.

The full v0.1 NPU ABI should extend this pattern:

```text
MMIO control registers
command queue
DMA descriptors
scratchpad allocation
INT8/INT4 GEMM commands
completion interrupt
performance counters
```

Current integration is still an MMIO-visible datapath model. The DMA block
tracks aligned 32-bit beat issue, byte completion, last source/destination
addresses, and final write strobe, but it does not yet drive a real memory
master or feed an NPU scratchpad/command queue.
