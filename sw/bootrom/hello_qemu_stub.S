    .section .text
    .globl _start
_start:
    la a0, message
    li a1, 0x10000000
1:
    lbu a2, 0(a0)
    beqz a2, 2f
    sb a2, 0(a1)
    addi a0, a0, 1
    j 1b
2:
    wfi
    j 2b

    .section .rodata
message:
    .asciz "openphone hello qemu\n"
