# Board smoke test plan

The board smoke firmware runs on an external MCU/debug adapter and exercises the demo chip through the debug/MMIO interface.

Pass criteria:

1. Hold reset low and verify GPIO/IRQ outputs low.
2. Release reset and wait 16 clock cycles.
3. Read boot ROM word 0: expect `0x4F50534F`.
4. Read boot ROM word 1: expect `0x43484950`.
5. Write `SCRATCH = 0xA5A55A5A`, read it back.
6. Write `GPIO_OUT = 0xA5`, verify LED/test-point state.
7. Configure timer compare and observe `IRQ_TIMER`.
8. Program DMA start and observe `IRQ_DMA`.
9. Program NPU operands `17 + 25`, observe `IRQ_NPU`, read result `42`.
10. Enable display block and observe `IRQ_VSYNC`.

Any mismatch is a first-article failure until explained by an approved waiver.
