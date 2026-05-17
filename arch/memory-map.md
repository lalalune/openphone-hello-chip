# Memory map

All addresses are byte addresses. The hello chip uses a single-cycle MMIO request interface. Only word-aligned accesses in the first 256 bytes of each 4 KiB region are implemented in the current RTL. Nonzero `addr[11:8]`, unaligned accesses, and unknown regions return `0xDEAD_BEEF` at the top-level decode.

| Region | Base | Size | Purpose |
| --- | ---: | ---: | --- |
| Boot ROM | `0x0000_0000` | `4 KiB` | Reset/identity words |
| Peripheral control | `0x1000_0000` | `4 KiB` | ID, scratch, GPIO, timer |
| DMA | `0x1001_0000` | `4 KiB` | DMA command/status stub |
| NPU | `0x1002_0000` | `4 KiB` | NPU command/status stub |
| Display | `0x1003_0000` | `4 KiB` | Framebuffer/display stub |

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
| `0x00` | `SRC` | RW | Source address placeholder |
| `0x04` | `DST` | RW | Destination address placeholder |
| `0x08` | `LEN` | RW | Byte length placeholder |
| `0x0C` | `CTRL_STATUS` | RW | Write bit 0 to start, bit 1 to clear done; read bit 0 busy, bit 1 done |

## NPU registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `OP_A` | RW | Operand A |
| `0x04` | `OP_B` | RW | Operand B |
| `0x08` | `RESULT` | RO | `OP_A + OP_B` for hello command |
| `0x0C` | `CTRL_STATUS` | RW | Write bit 0 to start, bit 1 to clear done; read bit 0 busy, bit 1 done |

## Display registers

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `FB_BASE` | RW | Framebuffer base placeholder |
| `0x04` | `MODE` | RW | `{height[15:0], width[15:0]}` |
| `0x08` | `FORMAT` | RW | FourCC-like format value |
| `0x0C` | `ENABLE` | RW | Bit 0 enables scanout |
| `0x10` | `VSYNC` | RO | Bit 0 is vsync IRQ level |
