#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
	echo "usage: $0 /path/to/linux" >&2
	exit 2
fi

linux=$1
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
bsp="$repo_root/sw/linux"

if [ ! -f "$linux/Kconfig" ] || [ ! -d "$linux/drivers" ] || [ ! -d "$linux/arch" ]; then
	echo "error: $linux does not look like a Linux kernel checkout" >&2
	exit 1
fi

printf 'Import commands:\n'
printf '  mkdir -p %s/drivers/misc/openphone-hello %s/arch/riscv/boot/dts/openphone\n' "$linux" "$linux"
printf '  rsync -a %s/drivers/hello/ %s/drivers/misc/openphone-hello/\n' "$bsp" "$linux"
printf '  cp %s/dts/openphone-hello.dts %s/arch/riscv/boot/dts/openphone/\n' "$bsp" "$linux"
printf 'Then add these fragments in the external Linux tree:\n'
printf '  drivers/misc/Kconfig: source "drivers/misc/openphone-hello/Kconfig"\n'
printf '  drivers/misc/Makefile: obj-$(CONFIG_OPENPHONE_HELLO_BSP) += openphone-hello/\n'
