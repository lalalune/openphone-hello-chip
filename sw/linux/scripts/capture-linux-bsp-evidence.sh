#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 /path/to/linux preflight|kernel-build|dtb-check|smoke" >&2
	exit 2
fi

linux=$1
mode=$2
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../../.." && pwd)
evidence_dir="$repo_root/docs/evidence/linux"
jobs=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)}
cross_compile=${CROSS_COMPILE:-}

if [ ! -f "$linux/Kconfig" ] || [ ! -d "$linux/drivers" ] || [ ! -d "$linux/arch" ]; then
	echo "error: $linux does not look like a Linux kernel checkout" >&2
	exit 1
fi

mkdir -p "$evidence_dir"

repo_status_command="python3 $repo_root/scripts/check_linux_external_bsp.py $linux"

require_imported_bsp() {
	missing=0
	for path in \
		"$linux/drivers/misc/openphone-hello/Kconfig" \
		"$linux/drivers/misc/openphone-hello/Makefile" \
		"$linux/drivers/misc/openphone-hello/hello-npu.c" \
		"$linux/drivers/misc/openphone-hello/hello-dma.c" \
		"$linux/drivers/misc/openphone-hello/hello_platform_contract.h" \
		"$linux/arch/riscv/boot/dts/openphone/openphone-hello.dts"; do
		if [ ! -f "$path" ]; then
			echo "STATUS: BLOCKED linux.capture-preflight - missing imported BSP file $path" >&2
			missing=1
		fi
	done
	if ! grep -Fqx 'source "drivers/misc/openphone-hello/Kconfig"' "$linux/drivers/misc/Kconfig" 2>/dev/null; then
		echo 'STATUS: BLOCKED linux.capture-preflight - drivers/misc/Kconfig does not source openphone-hello/Kconfig' >&2
		missing=1
	fi
	if ! grep -Fqx 'obj-$'"(CONFIG_OPENPHONE_HELLO_BSP)"' += openphone-hello/' "$linux/drivers/misc/Makefile" 2>/dev/null; then
		echo 'STATUS: BLOCKED linux.capture-preflight - drivers/misc/Makefile does not include openphone-hello/' >&2
		missing=1
	fi
	if [ "$missing" -ne 0 ]; then
		echo "next: sw/linux/scripts/import-linux-bsp.sh $linux" >&2
		$repo_status_command >/dev/null || true
		exit 2
	fi
}

require_riscv_compiler() {
	if [ -n "$cross_compile" ]; then
		if ! command -v "${cross_compile}gcc" >/dev/null 2>&1; then
			echo "STATUS: BLOCKED linux.capture-preflight - CROSS_COMPILE compiler not found: ${cross_compile}gcc" >&2
			$repo_status_command >/dev/null || true
			exit 2
		fi
	elif ! command -v riscv64-linux-gnu-gcc >/dev/null 2>&1 && \
		! command -v riscv64-unknown-linux-gnu-gcc >/dev/null 2>&1; then
		echo "STATUS: BLOCKED linux.capture-preflight - set CROSS_COMPILE or install riscv64 Linux compiler" >&2
		$repo_status_command >/dev/null || true
		exit 2
	fi
}

timestamp_utc() {
	date -u '+%Y-%m-%dT%H:%M:%SZ'
}

record_command() {
	artifact=$1
	log=$2
	command=$3
	{
		echo "openphone-evidence: target=linux artifact=$artifact"
		echo "openphone-evidence: status_command=$repo_status_command"
		echo "openphone-evidence: command=$command"
		started=$(timestamp_utc)
		echo "openphone-evidence: started_utc=$started"
		echo "openphone-evidence: linux=$linux"
		echo "openphone-evidence: cross_compile=$cross_compile"
		echo "EXTERNAL_TREE=$linux"
		echo "COMMAND=$command"
		echo "START_UTC=$started"
	} > "$log"
	set +e
	(cd "$linux" && sh -c "$command") >> "$log" 2>&1
	rc=$?
	set -e
	if [ "$rc" -eq 0 ]; then
		if [ "$artifact" = "hello-mmio-smoke" ]; then
			echo "HELLO_MMIO_SMOKE_PASS" >> "$log"
		fi
		echo "openphone-evidence: status=PASS" >> "$log"
		echo "RESULT=PASS" >> "$log"
	else
		echo "openphone-evidence: status=FAIL rc=$rc" >> "$log"
		echo "RESULT=FAIL rc=$rc" >> "$log"
	fi
	ended=$(timestamp_utc)
	echo "openphone-evidence: ended_utc=$ended" >> "$log"
	echo "END_UTC=$ended" >> "$log"
	exit "$rc"
}

make_prefix="make ARCH=riscv"
if [ -n "$cross_compile" ]; then
	make_prefix="$make_prefix CROSS_COMPILE=$cross_compile"
fi
dt_schema_files="Documentation/devicetree/bindings/openphone/openphone,hello-npu.yaml Documentation/devicetree/bindings/openphone/openphone,hello-dma.yaml Documentation/devicetree/bindings/openphone/openphone,hello-display.yaml Documentation/devicetree/bindings/openphone/openphone,hello-gpio.yaml"

case "$mode" in
	preflight)
		$repo_status_command
		;;
	kernel-build)
		require_imported_bsp
		require_riscv_compiler
		record_command \
			openphone_hello_kernel_build \
			"$evidence_dir/openphone_hello_kernel_build.log" \
			"test -f .config && $make_prefix -j$jobs Image dtbs modules && grep -R \"CONFIG_OPENPHONE_HELLO\" .config include/config 2>/dev/null && test -f arch/riscv/boot/Image"
		;;
	dtb-check)
		require_imported_bsp
		record_command \
			openphone_hello_dtb_check \
			"$evidence_dir/openphone_hello_dtb_check.log" \
			"$make_prefix dtbs_check DT_SCHEMA_FILES=\"$dt_schema_files\" && grep -R \"openphone,hello-npu\" arch/riscv/boot/dts/openphone && grep -R \"openphone,hello-dma\" arch/riscv/boot/dts/openphone && grep -R \"openphone,hello-display\" arch/riscv/boot/dts/openphone"
		;;
	smoke)
		if [ -z "${HELLO_SMOKE_CMD:-}" ]; then
			echo "error: HELLO_SMOKE_CMD is required, for example: ssh root@TARGET /tmp/hello-mmio-smoke" >&2
			exit 2
		fi
		record_command \
			hello-mmio-smoke \
			"$evidence_dir/hello-mmio-smoke.log" \
			"$HELLO_SMOKE_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
