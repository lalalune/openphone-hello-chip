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
		"$linux/drivers/misc/openagent-e1/Kconfig" \
		"$linux/drivers/misc/openagent-e1/Makefile" \
		"$linux/drivers/misc/openagent-e1/e1-npu.c" \
		"$linux/drivers/misc/openagent-e1/e1-dma.c" \
		"$linux/drivers/misc/openagent-e1/e1_platform_contract.h" \
		"$linux/arch/riscv/boot/dts/openagent/openagent-e1.dts"; do
		if [ ! -f "$path" ]; then
			echo "STATUS: BLOCKED linux.capture-preflight - missing imported BSP file $path" >&2
			missing=1
		fi
	done
	if ! grep -Fqx 'source "drivers/misc/openagent-e1/Kconfig"' "$linux/drivers/misc/Kconfig" 2>/dev/null; then
		echo 'STATUS: BLOCKED linux.capture-preflight - drivers/misc/Kconfig does not source openagent-e1/Kconfig' >&2
		missing=1
	fi
	if ! grep -Fqx 'obj-$'"(CONFIG_OPENAGENT_E1_BSP)"' += openagent-e1/' "$linux/drivers/misc/Makefile" 2>/dev/null; then
		echo 'STATUS: BLOCKED linux.capture-preflight - drivers/misc/Makefile does not include openagent-e1/' >&2
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
		echo "openagent-evidence: target=linux artifact=$artifact"
		echo "openagent-evidence: status_command=$repo_status_command"
		echo "openagent-evidence: command=$command"
		started=$(timestamp_utc)
		echo "openagent-evidence: started_utc=$started"
		echo "openagent-evidence: linux=$linux"
		echo "openagent-evidence: cross_compile=$cross_compile"
		echo "EXTERNAL_TREE=$linux"
		echo "COMMAND=$command"
		echo "START_UTC=$started"
	} > "$log"
	set +e
	(cd "$linux" && sh -c "$command") >> "$log" 2>&1
	rc=$?
	set -e
	if [ "$rc" -eq 0 ]; then
		if [ "$artifact" = "e1-mmio-smoke" ]; then
			echo "E1_MMIO_SMOKE_PASS" >> "$log"
		fi
		echo "openagent-evidence: status=PASS" >> "$log"
		echo "RESULT=PASS" >> "$log"
	else
		echo "openagent-evidence: status=FAIL rc=$rc" >> "$log"
		echo "RESULT=FAIL rc=$rc" >> "$log"
	fi
	ended=$(timestamp_utc)
	echo "openagent-evidence: ended_utc=$ended" >> "$log"
	echo "END_UTC=$ended" >> "$log"
	exit "$rc"
}

make_prefix="make ARCH=riscv"
if [ -n "$cross_compile" ]; then
	make_prefix="$make_prefix CROSS_COMPILE=$cross_compile"
fi
dt_schema_files="Documentation/devicetree/bindings/openagent/openagent,e1-npu.yaml Documentation/devicetree/bindings/openagent/openagent,e1-dma.yaml Documentation/devicetree/bindings/openagent/openagent,e1-display.yaml Documentation/devicetree/bindings/openagent/openagent,e1-gpio.yaml"

case "$mode" in
	preflight)
		$repo_status_command
		;;
	kernel-build)
		require_imported_bsp
		require_riscv_compiler
		record_command \
			openagent_e1_kernel_build \
			"$evidence_dir/openagent_e1_kernel_build.log" \
			"test -f .config && $make_prefix -j$jobs Image dtbs modules && grep -R \"CONFIG_OPENAGENT_E1\" .config include/config 2>/dev/null && test -f arch/riscv/boot/Image"
		;;
	dtb-check)
		require_imported_bsp
		record_command \
			openagent_e1_dtb_check \
			"$evidence_dir/openagent_e1_dtb_check.log" \
			"$make_prefix dtbs_check DT_SCHEMA_FILES=\"$dt_schema_files\" && grep -R \"openagent,e1-npu\" arch/riscv/boot/dts/openagent && grep -R \"openagent,e1-dma\" arch/riscv/boot/dts/openagent && grep -R \"openagent,e1-display\" arch/riscv/boot/dts/openagent"
		;;
	smoke)
		if [ -z "${E1_SMOKE_CMD:-}" ]; then
			echo "error: E1_SMOKE_CMD is required, for example: ssh root@TARGET /tmp/e1-mmio-smoke" >&2
			exit 2
		fi
		record_command \
			e1-mmio-smoke \
			"$evidence_dir/e1-mmio-smoke.log" \
			"$E1_SMOKE_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
