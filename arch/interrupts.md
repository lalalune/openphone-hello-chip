# Interrupt map

The hello chip exposes level-style interrupt outputs. The full SoC will route equivalent sources through a PLIC or IMSIC-compatible interrupt controller.

| Signal | Source | Meaning |
| --- | --- | --- |
| `irq_timer` | Peripheral block | Timer count reached compare |
| `irq_dma` | DMA block | DMA command finished |
| `irq_npu` | NPU block | NPU command finished |
| `irq_vsync` | Display block | Display vsync pulse/level placeholder |

The full-chip interrupt map must preserve stable source IDs in `arch/interrupts.md` as PLIC/IMSIC integration is added.
