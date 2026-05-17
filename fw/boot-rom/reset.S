/*
 * fw/boot-rom/reset.S
 *
 * v0 OpenPhone boot ROM stub. Lives at architectural reset vector
 * 0x0000_1000 (see docs/arch/boot-rom-spec.md). This is the minimum
 * RV64 reset path that the Chipyard Rocket wrapper will jump into.
 *
 * It does:
 *   - select hart 0, park any other hart in a wfi loop
 *   - clear interrupts, satp, pmpcfg0
 *   - set mtvec to a halting trap shim
 *   - hand off to the OpenSBI entry address at OPENSBI_ENTRY
 *
 * It does NOT yet verify a signature, read OTP, parse a firmware header,
 * or relocate an image. The OpenSBI handoff ABI is documented in
 * docs/arch/boot-rom-spec.md.
 *
 * Build:
 *   make -C fw/boot-rom hello_boot_rom.bin
 * Produces .bin (Chipyard BootROMParams.contentFileName) and .hex
 * (consumed by $readmemh in any future contract ROM model).
 */

    .section .text.reset, "ax"
    .globl _reset
    .option norvc

#ifndef OPENSBI_ENTRY
/* DRAM base + 0x80000 is the conventional OpenSBI fw_jump entry. */
#define OPENSBI_ENTRY 0x0000000080080000
#endif

#ifndef BOOT_STATUS_MAILBOX
#define BOOT_STATUS_MAILBOX 0x0000000000002000
#endif

#ifndef FDT_ADDR
/* Per docs/arch/boot-rom-spec.md, FDT lands at end of image rounded up
 * to 2MiB. For the v0 stub we hard-code a known DRAM offset; the loader
 * will overwrite this once a real image header is parsed.
 */
#define FDT_ADDR 0x00000000A0000000
#endif

_reset:
    /* Park non-zero harts. */
    csrr    t0, mhartid
    bnez    t0, _park

    /* Mask all interrupts and clear pending. */
    csrw    mie, zero
    csrw    mip, zero
    li      t0, 0x00001800            /* MPP = M (3), MPIE/MIE = 0 */
    csrw    mstatus, t0

    /* MMU off, no PMP, no scratch. */
    csrw    satp, zero
    csrw    pmpcfg0, zero
    csrw    pmpaddr0, zero
    csrw    mscratch, zero

    /* Trap shim catches any pre-handoff exception. */
    la      t0, _trap_shim
    csrw    mtvec, t0

    /* fence + ifence before handing off. */
    fence   rw, rw
    fence.i

    /* a0 = hartid, a1 = FDT phys addr, a2 = 0 (reserved). */
    csrr    a0, mhartid
    li      a1, FDT_ADDR
    li      a2, 0

    /* Jump to OpenSBI M-mode entry. */
    li      t0, OPENSBI_ENTRY
    jr      t0

_park:
    wfi
    j       _park

    .balign 16
_trap_shim:
    /* Pre-handoff trap: write 0xDEADBEEF to boot status mailbox and halt. */
    li      t0, BOOT_STATUS_MAILBOX
    li      t1, 0xDEADBEEF
    sw      t1, 0(t0)
1:  wfi
    j       1b
