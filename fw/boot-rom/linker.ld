/* fw/boot-rom/linker.ld
 *
 * Boot ROM layout for the v0 OpenPhone reset stub. The ROM aperture is
 * 0x0000_1000..0x0000_1FFF (4 KiB) per docs/arch/boot-rom-spec.md.
 * The reset vector is the first byte of the .text.reset section.
 */
OUTPUT_ARCH("riscv")
ENTRY(_reset)

MEMORY
{
    ROM (rx) : ORIGIN = 0x00001000, LENGTH = 0x1000
}

SECTIONS
{
    .text.reset : {
        KEEP(*(.text.reset))
        *(.text*)
        . = ALIGN(4);
    } > ROM

    .rodata : {
        *(.rodata*)
        . = ALIGN(4);
    } > ROM

    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
