# Memory map

All addresses are byte addresses. The hello chip uses a single-cycle MMIO request interface. Only word-aligned accesses in the first 256 bytes of each 4 KiB region are implemented in the current RTL. Nonzero `addr[11:8]`, unaligned accesses, and unknown regions return `0xDEAD_BEEF` at the top-level decode.

| Region | Base | Size | Purpose |
| --- | ---: | ---: | --- |
| Boot ROM | `0x0000_0000` | `4 KiB` | Reset/identity words |
| Peripheral control | `0x1000_0000` | `4 KiB` | ID, scratch, GPIO, timer |
| DMA | `0x1001_0000` | `4 KiB` | DMA master contract model |
| NPU | `0x1002_0000` | `4 KiB` | Small NPU datapath |
| Display | `0x1003_0000` | `4 KiB` | Framebuffer scanout controller |
| DRAM aperture | `0x8000_0000` | `4 KiB` | SRAM-backed test DRAM visible to debug MMIO and DMA |

## Linux-capable AXI-Lite scaffold map

The CPU/interconnect scaffold is separate from the hello-chip debug MMIO path. It uses AXI-Lite-style channels and establishes the future software contract. The hello-chip top now exposes a small debug-visible DRAM aperture for DMA integration, while the Linux-capable scaffold keeps its own AXI-Lite DRAM model:

| Region | Base | Size | Purpose |
| --- | ---: | ---: | --- |
| Interrupt controller | `0x0C00_0000` | `4 KiB` | PLIC-style source pending, enable, claim/complete scaffold |
| DMA control scaffold | `0x1001_0000` | `4 KiB` | AXI-Lite decode slot; currently tied off in the Linux scaffold |
| DRAM aperture | `0x8000_0000` | `256 MiB` | External DRAM controller/PHY boundary; current RTL model implements a small test memory |

Unmapped AXI-Lite scaffold accesses return `DECERR`; reads also return `0xDEAD_BEEF`.

## Linux-capable CPU SoC variant (generated artifacts)

The Linux-capable CPU SoC variant of the hello chip is defined by the
`hello_chip_cpu_variant` section of `sw/platform/hello_platform_contract.json`.
That section is the single source of truth for the boot vector, DRAM map,
PLIC/CLINT bases, UART, timer, DMA, NPU, display, and IRQ assignments.

The following files under `sw/platform/generated/` are produced by
`scripts/gen_platform_artifacts.py` (also reachable via
`make platform-artifacts`) and MUST NOT be edited by hand:

| Artifact | Consumer |
| --- | --- |
| `sw/platform/generated/hello_platform.vh`       | RTL decode / Verilog headers |
| `sw/platform/generated/hello-platform.dtsi`     | Linux kernel DTS includes |
| `sw/platform/generated/hello_platform.h`        | U-Boot, OpenSBI, bare-metal firmware |
| `sw/platform/generated/hello_platform_hal.json` | AOSP HAL configs |

`make platform-contract-check` runs `scripts/gen_platform_artifacts.py
--check` and `scripts/check_platform_contract.py`, which together fail CI
if any artifact is stale or if a handwritten DTS consumer references one
of the contract device compatibles at a base address that does not match
the contract.

The tiny CPU execution test uses the DRAM aperture as instruction and data memory. The current DRAM model implements aligned 32-bit words with byte strobes; the CPU subset only generates aligned `LW` and `SW`.

## Register conventions

All registers are 32-bit little-endian words. Writes to reserved registers are ignored. Reads from unmapped regions return `0xDEAD_BEEF`.

## Peripheral registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `ID` | RO | `0x1000_0001` |
| `0x04` | `SCRATCH` | RW | Software scratch register |
| `0x08` | `GPIO_OUT` | RW | Low 8 bits drive `gpio_out` |
| `0x0C` | `TIMER_COUNT` | RO | Free-running counter |
| `0x10` | `TIMER_COMPARE` | RW | Timer interrupt threshold |
| `0x14` | `TIMER_IRQ` | RO | Bit 0 is timer IRQ level |

## DMA registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `SRC` | RW | Source byte address; must be word-aligned in this model |
| `0x04` | `DST` | RW | Destination byte address; must be word-aligned in this model |
| `0x08` | `LEN` | RW | Byte length; the model issues one 32-bit beat at a time |
| `0x0C` | `CTRL_STATUS` | RW | Write bit 0 to start, bit 1 to clear done/error; read bit 0 busy, bit 1 done/IRQ, bit 2 error, bit 3 accepted read-address pulse, bit 4 accepted write-address/data pulse |
| `0x10` | `CFG` | RW | Reserved DMA integration/configuration word; reset value is `4` bytes per beat |
| `0x14` | `BYTES_DONE` | RO | Number of payload bytes completed by the current/last command |
| `0x18` | `BEATS_ISSUED` | RO | Number of modeled write beats completed |
| `0x1C` | `CUR_SRC` | RO | Current source address while busy |
| `0x20` | `CUR_DST` | RO | Current destination address while busy |
| `0x24` | `LAST_SRC` | RO | Last modeled read address issued |
| `0x28` | `LAST_DST` | RO | Last modeled write address issued |
| `0x2C` | `MASTER_TRACE` | RO | `{last_wstrb[3:0], state[2:0]}` packed into bits `[10:7]` and `[2:0]` |
| `0x30` | `READ_BEATS` | RO | Number of AXI-Lite read responses completed |
| `0x34` | `WRITE_BEATS` | RO | Number of AXI-Lite write responses completed |
| `0x38` | `ERROR_COUNT` | RO | Number of alignment or bus response errors observed by the current/last command |

## NPU registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `OP_A` | RW | Operand A |
| `0x04` | `OP_B` | RW | Operand B |
| `0x08` | `RESULT` | RO | Low result word |
| `0x0C` | `CTRL_STATUS` | RW | Write bit 0 to start, bit 1 to clear done/error; read bit 0 busy, bit 1 done/IRQ, bit 2 error |
| `0x10` | `OPCODE` | RW | `0` add, `1` sub, `2` unsigned multiply, `3` signed S16 MAC, `4` packed signed INT8 dot4, `5` unsigned max, `6` unsigned min |
| `0x14` | `ACC` | RW | Accumulator/bias input for MAC and DOT4 |
| `0x18` | `RESULT_HI` | RO | High result/sign-extension word |
| `0x1C` | `TRACE` | RO | `{latched_opcode[3:0], busy_count[2:0]}` in low bits |

## Display registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `FB_BASE` | RW | Framebuffer base address; top-level scanout currently fetches from the `0x8000_0000` SRAM-backed DRAM aperture |
| `0x04` | `MODE` | RW | `{height[15:0], width[15:0]}` |
| `0x08` | `FORMAT` | RW | FourCC-like format value |
| `0x0C` | `ENABLE` | RW | Bit 0 enables scanout |
| `0x10` | `VSYNC` | RO | Bit 0 is vsync IRQ level |
| `0x14` | `UNDERFLOW_COUNT` | RW1C-like | Counts active pixels that could not fetch framebuffer data |
| `0x18` | `FETCHED_PIXEL_COUNT` | RW1C-like | Counts active pixels fetched from the framebuffer client |

## Interrupt controller registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `ID` | RO | `0x1C00_0001` |
| `0x04` | `PENDING` | RO | Bit `n` is pending state for source ID `n + 1` |
| `0x08` | `ENABLE` | RW | Bit `n` enables source ID `n + 1` |
| `0x0C` | `CLAIM_COMPLETE` | RW | Read returns lowest enabled pending source ID, or 0; write source ID to clear its pending bit |
