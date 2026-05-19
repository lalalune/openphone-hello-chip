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
generated="$repo_root/sw/platform/generated"

if [ ! -f "$linux/Kconfig" ] || [ ! -d "$linux/drivers" ] || [ ! -d "$linux/arch" ]; then
	echo "error: $linux does not look like a Linux kernel checkout" >&2
	exit 1
fi

ensure_line() {
	file=$1
	line=$2
	if [ ! -f "$file" ]; then
		echo "error: cannot update missing external file $file" >&2
		exit 1
	fi
	if ! grep -Fqx "$line" "$file"; then
		printf '\n%s\n' "$line" >> "$file"
	fi
}

printf 'Import commands:\n'
printf '  mkdir -p %s/drivers/misc/openphone-hello %s/arch/riscv/boot/dts/openphone %s/Documentation/devicetree/bindings/openphone %s/kernel/configs\n' "$linux" "$linux" "$linux" "$linux"
printf '  rsync -a %s/drivers/hello/ %s/drivers/misc/openphone-hello/\n' "$bsp" "$linux"
printf '  cp %s/dts/openphone-hello.dts %s/dts/Makefile %s/arch/riscv/boot/dts/openphone/\n' "$bsp" "$bsp" "$linux"
printf '  cp %s/hello-platform.dtsi %s/arch/riscv/boot/dts/openphone/\n' "$generated" "$linux"
printf '  cp %s/Documentation/devicetree/bindings/openphone/*.yaml %s/Documentation/devicetree/bindings/openphone/\n' "$bsp" "$linux"
printf '  cp %s/hello_platform_contract.h %s/drivers/misc/openphone-hello/hello_platform_contract.h\n' "$generated" "$linux"
printf '  cp %s/configs/openphone_hello.fragment %s/kernel/configs/openphone_hello.config\n' "$bsp" "$linux"
printf 'Then add these fragments in the external Linux tree:\n'
printf '  drivers/misc/Kconfig: source "drivers/misc/openphone-hello/Kconfig"\n'
# shellcheck disable=SC2016
printf '  drivers/misc/Makefile: obj-$(CONFIG_OPENPHONE_HELLO_BSP) += openphone-hello/\n'
printf '  arch/riscv/boot/dts/Makefile: subdir-y += openphone\n'
printf 'Capture real evidence back in this repository:\n'
printf '  (cd %s && make ARCH=riscv openphone_hello.config olddefconfig)\n' "$linux"
printf '  python3 %s/scripts/check_linux_external_bsp.py %s\n' "$repo_root" "$linux"
printf '  %s/sw/linux/scripts/capture-linux-bsp-evidence.sh %s kernel-build\n' "$repo_root" "$linux"
printf '  %s/sw/linux/scripts/capture-linux-bsp-evidence.sh %s dtb-check\n' "$repo_root" "$linux"
printf '  HELLO_SMOKE_CMD='\''ssh root@TARGET /usr/bin/hello-mmio-smoke'\'' %s/sw/linux/scripts/capture-linux-bsp-evidence.sh %s smoke\n' "$repo_root" "$linux"

if [ "$check_only" -eq 0 ]; then
	mkdir -p \
		"$linux/drivers/misc/openphone-hello" \
		"$linux/arch/riscv/boot/dts/openphone" \
		"$linux/Documentation/devicetree/bindings/openphone" \
		"$linux/kernel/configs"
	rsync -a "$bsp/drivers/hello/" "$linux/drivers/misc/openphone-hello/"
	cp "$bsp/dts/openphone-hello.dts" "$bsp/dts/Makefile" "$linux/arch/riscv/boot/dts/openphone/"
	cp "$generated/hello-platform.dtsi" "$linux/arch/riscv/boot/dts/openphone/"
	cp "$bsp"/Documentation/devicetree/bindings/openphone/*.yaml \
		"$linux/Documentation/devicetree/bindings/openphone/"
	cp "$generated/hello_platform_contract.h" "$linux/drivers/misc/openphone-hello/hello_platform_contract.h"
	cp "$bsp/configs/openphone_hello.fragment" "$linux/kernel/configs/openphone_hello.config"
	ensure_line "$linux/drivers/misc/Kconfig" 'source "drivers/misc/openphone-hello/Kconfig"'
	ensure_line "$linux/drivers/misc/Makefile" 'obj-$'"(CONFIG_OPENPHONE_HELLO_BSP)"' += openphone-hello/'
	ensure_line "$linux/arch/riscv/boot/dts/Makefile" 'subdir-y += openphone'
	printf 'Imported OpenPhone Linux BSP files into the external kernel tree.\n'
fi

if [ "$check_only" -eq 1 ]; then
	missing=0
	for path in \
		"$bsp/drivers/hello/Kconfig" \
		"$bsp/drivers/hello/Makefile" \
		"$bsp/drivers/hello/hello-npu-uapi.h" \
		"$bsp/drivers/hello/hello-npu.c" \
		"$bsp/drivers/hello/hello-dma.c" \
		"$bsp/tests/hello-npu-smoke.c" \
		"$bsp/dts/openphone-hello.dts" \
		"$bsp/dts/Makefile" \
		"$generated/hello-platform.dtsi" \
		"$bsp/configs/openphone_hello.fragment" \
		"$generated/hello_platform_contract.h"; do
		if [ ! -f "$path" ]; then
			echo "FAIL: missing repo artifact ${path#"$repo_root"/}" >&2
			missing=1
		fi
	done
	if ! ls "$bsp"/Documentation/devicetree/bindings/openphone/*.yaml >/dev/null 2>&1; then
		echo "FAIL: missing repo artifact sw/linux/Documentation/devicetree/bindings/openphone/*.yaml" >&2
		missing=1
	fi
	if [ "$missing" -ne 0 ]; then
		exit 1
	fi
	echo "STATUS: PASS linux.import-check - external Linux checkout shape and repo BSP inputs are present"
	echo "STATUS: BLOCKED linux.build-evidence - run scripts/check_linux_external_bsp.py and the external kernel/Image/DTB capture commands"
fi
