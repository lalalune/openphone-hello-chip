#!/usr/bin/env sh
set -eu

check_only=0

if [ "${1:-}" = "--check" ]; then
	check_only=1
	shift
fi

if [ "$#" -ne 1 ]; then
	echo "usage: $0 [--check] /path/to/linux" >&2
	exit 2
fi

linux=$1
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../../.." && pwd)
bsp="$repo_root/sw/linux"

if [ ! -f "$linux/Kconfig" ] || [ ! -d "$linux/drivers" ] || [ ! -d "$linux/arch" ]; then
	echo "error: $linux does not look like a Linux kernel checkout" >&2
	exit 1
fi

printf 'Import commands:\n'
printf '  mkdir -p %s/drivers/misc/openphone-hello %s/arch/riscv/boot/dts/openphone\n' "$linux" "$linux"
printf '  rsync -a %s/drivers/hello/ %s/drivers/misc/openphone-hello/\n' "$bsp" "$linux"
printf '  cp %s/dts/openphone-hello.dts %s/arch/riscv/boot/dts/openphone/\n' "$bsp" "$linux"
printf '  cp %s/sw/platform/generated/hello_platform_contract.h %s/drivers/misc/openphone-hello/hello_platform_contract.h\n' "$repo_root" "$linux"
printf 'Then add these fragments in the external Linux tree:\n'
printf '  drivers/misc/Kconfig: source "drivers/misc/openphone-hello/Kconfig"\n'
# shellcheck disable=SC2016
printf '  drivers/misc/Makefile: obj-$(CONFIG_OPENPHONE_HELLO_BSP) += openphone-hello/\n'
printf 'Capture real evidence back in this repository:\n'
# shellcheck disable=SC2016
printf '  { printf "EXTERNAL_TREE=%s\\nCOMMAND=make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- Image dtbs modules\\nSTART_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\n"; make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- Image dtbs modules; rc=$?; printf "END_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\nRESULT=$rc\\n"; exit $rc; } 2>&1 | tee %s/docs/evidence/linux/openphone_hello_kernel_build.log\n' "$linux" "$repo_root"
# shellcheck disable=SC2016
printf '  { printf "EXTERNAL_TREE=%s\\nCOMMAND=make ARCH=riscv dtbs_check DT_SCHEMA_FILES=openphone\\nSTART_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\n"; make ARCH=riscv dtbs_check DT_SCHEMA_FILES=openphone; rc=$?; printf "END_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\nRESULT=$rc\\n"; exit $rc; } 2>&1 | tee %s/docs/evidence/linux/openphone_hello_dtb_check.log\n' "$linux" "$repo_root"

if [ "$check_only" -eq 0 ]; then
	mkdir -p "$linux/drivers/misc/openphone-hello" "$linux/arch/riscv/boot/dts/openphone"
	rsync -a "$bsp/drivers/hello/" "$linux/drivers/misc/openphone-hello/"
	cp "$bsp/dts/openphone-hello.dts" "$linux/arch/riscv/boot/dts/openphone/"
	cp "$repo_root/sw/platform/generated/hello_platform_contract.h" "$linux/drivers/misc/openphone-hello/hello_platform_contract.h"
	printf 'Imported OpenPhone Linux BSP files into the external kernel tree.\n'
fi

if [ "$check_only" -eq 1 ]; then
	missing=0
	for path in \
		"$bsp/drivers/hello/Kconfig" \
		"$bsp/drivers/hello/Makefile" \
		"$bsp/drivers/hello/hello-npu.c" \
		"$bsp/drivers/hello/hello-dma.c" \
		"$bsp/dts/openphone-hello.dts" \
		"$repo_root/sw/platform/generated/hello_platform_contract.h"; do
		if [ ! -f "$path" ]; then
				echo "FAIL: missing repo artifact ${path#"$repo_root"/}" >&2
			missing=1
		fi
	done
	if [ "$missing" -ne 0 ]; then
		exit 1
	fi
	echo "STATUS: PASS linux.import-check - external Linux checkout shape and repo BSP inputs are present"
	echo "STATUS: BLOCKED linux.build-evidence - run external kernel Image/dtbs/modules build and archive docs/evidence/linux/*.log"
fi
