# Tier 1 OpenSBI S-mode payload.

CROSS    ?= riscv64-unknown-elf-
CC       := $(CROSS)gcc
OBJCOPY  := $(CROSS)objcopy

CFLAGS   := -nostdlib -nostartfiles -ffreestanding -fno-pic \
            -mcmodel=medany -march=rv64imac -mabi=lp64 \
            -O2 -Wall -Wextra -g
LDFLAGS  := -Wl,-T,linker.ld -Wl,--no-warn-rwx-segments

OBJS := reset.o hello.o
TARGET := hello

.PHONY: all clean
all: $(TARGET).elf $(TARGET).bin

%.o: %.S
	$(CC) $(CFLAGS) -c $< -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(OBJS) linker.ld
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o $(TARGET).elf $(TARGET).bin
