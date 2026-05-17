#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 /path/to/u-boot build|boot-chain" >&2
	exit 2
fi

uboot=$1
mode=$2
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../.." && pwd)
evidence_dir="$repo_root/docs/evidence/linux"

if [ ! -f "$uboot/Makefile" ] || [ ! -d "$uboot/arch" ] || [ ! -d "$uboot/configs" ]; then
	echo "error: $uboot does not look like a U-Boot checkout" >&2
	exit 1
fi

mkdir -p "$evidence_dir"

timestamp_utc() {
	date -u '+%Y-%m-%dT%H:%M:%SZ'
}

record_uboot_command() {
	artifact=$1
	log=$2
	command=$3
	{
		echo "openphone-evidence: target=u-boot artifact=$artifact"
		echo "openphone-evidence: command=$command"
		echo "openphone-evidence: started_utc=$(timestamp_utc)"
		echo "openphone-evidence: uboot=$uboot"
	} > "$log"
	set +e
	(cd "$uboot" && sh -c "$command") >> "$log" 2>&1
	rc=$?
	set -e
	if [ "$rc" -eq 0 ]; then
		echo "openphone-evidence: status=PASS" >> "$log"
	else
		echo "openphone-evidence: status=FAIL rc=$rc" >> "$log"
	fi
	echo "openphone-evidence: ended_utc=$(timestamp_utc)" >> "$log"
	exit "$rc"
}

case "$mode" in
	build)
		if [ -z "${OPENPHONE_UBOOT_CMD:-}" ]; then
			echo "error: set OPENPHONE_UBOOT_CMD to the external U-Boot build command" >&2
			exit 2
		fi
		record_uboot_command \
			u_boot_openphone_build \
			"$evidence_dir/u_boot_openphone_build.log" \
			"$OPENPHONE_UBOOT_CMD"
		;;
	boot-chain)
		if [ -z "${OPENPHONE_UBOOT_BOOT_CMD:-}" ]; then
			echo "error: set OPENPHONE_UBOOT_BOOT_CMD to the external boot-chain command" >&2
			exit 2
		fi
		record_uboot_command \
			u_boot_opensbi_boot_chain \
			"$evidence_dir/u_boot_opensbi_boot_chain.log" \
			"$OPENPHONE_UBOOT_BOOT_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
