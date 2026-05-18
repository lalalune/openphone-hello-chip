#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 /path/to/linux kernel-build|dtb-check|smoke" >&2
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

timestamp_utc() {
	date -u '+%Y-%m-%dT%H:%M:%SZ'
}

record_command() {
	artifact=$1
	log=$2
	command=$3
	{
		echo "openphone-evidence: target=linux artifact=$artifact"
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

case "$mode" in
	kernel-build)
		record_command \
			openphone_hello_kernel_build \
			"$evidence_dir/openphone_hello_kernel_build.log" \
			"$make_prefix -j$jobs Image modules && grep -R \"CONFIG_OPENPHONE_HELLO\" .config include/config 2>/dev/null"
		;;
	dtb-check)
		record_command \
			openphone_hello_dtb_check \
			"$evidence_dir/openphone_hello_dtb_check.log" \
			"$make_prefix dtbs_check DT_SCHEMA_FILES=/openphone/ && grep -R \"openphone,hello-npu\" arch/riscv/boot/dts/openphone"
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
