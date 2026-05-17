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
`MAC_S16`/`DOT4_S8`/`DOT8_S4` results.

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
| `7` | `DOT8_S4` | eight packed signed INT4 products plus signed `ACC` |
| `8` | `GEMM_S8` | bounded scratchpad INT8 GEMM tile, signed int32 output |

Status bits:

| Bit | Name | Meaning |
| ---: | --- | --- |
| `0` | `busy` | Command is executing |
| `1` | `done` | Command completed; also drives `irq_npu` |
| `2` | `error` | Unsupported opcode was rejected |

Write `CTRL_STATUS[1]` to clear `done` and `error`. Operands are latched when
`start` is accepted; software should not rely on mid-command register writes
affecting the in-flight operation.

## Scratchpad GEMM prototype

`GEMM_S8` is a concrete tile prototype, not a tensor subsystem. Software stages
row-major signed INT8 `A` and `B` matrices into a 64-byte MMIO scratchpad and
programs a bounded command. The datapath performs one signed INT8 multiply
accumulate per cycle and writes row-major signed int32 `C` results back into the
scratchpad. The current RTL bounds are `M <= 3`, `N <= 3`, `K <= 7`, further
limited by the 64-byte scratchpad footprint.

Additional registers:

| Offset | Name | Fields |
| ---: | --- | --- |
| `0x20` | `GEMM_CFG` | `M[1:0]`, `N[9:8]`, `K[18:16]` |
| `0x24` | `GEMM_BASE` | byte bases: `A[5:0]`, `B[13:8]`, `C[21:16]` |
| `0x28` | `GEMM_STRIDE` | byte strides: `A[3:0]`, `B[11:8]`, `C[19:16]` |
| `0x2c` | `PERF_UNSUPPORTED_OPS` | unsupported opcode/configuration counter |
| `0x30` | `CMD_PARAM` | reserved command parameter word for future queue/runtime work |
| `0x40` | `DESC_BASE` | reserved descriptor base for future queue/runtime work |
| `0x44` | `DESC_HEAD` | reserved descriptor head for future queue/runtime work |
| `0x48` | `DESC_TAIL` | reserved descriptor tail for future queue/runtime work |
| `0x4c` | `DESC_STATUS` | reserved descriptor status for future queue/runtime work |
| `0x50` | `PERF_CYCLES` | cycles spent in active state |
| `0x54` | `PERF_MACS` | signed INT8 MAC operations issued |
| `0x58` | `PERF_OPS` | accepted operation counter |
| `0x5c` | `PERF_ERRORS` | rejected commands/configurations; write bit 0 to clear all perf counters |
| `0x80`-`0xbc` | `SCRATCH[0..15]` | 16 little-endian 32-bit scratchpad words |

For row-major `A[M][K]`, `B[K][N]`, and `C[M][N]`, use `A_STRIDE = K`,
`B_STRIDE = N`, and `C_STRIDE = 4*N`. `C_BASE` must be word-aligned. Invalid
dimensions or scratchpad addresses complete with `CTRL_STATUS.done|error` set
and increment `PERF_ERRORS`.

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
