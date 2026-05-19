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
		echo "openagent-evidence: target=u-boot artifact=$artifact"
		echo "openagent-evidence: command=$command"
		echo "openagent-evidence: started_utc=$(timestamp_utc)"
		echo "openagent-evidence: uboot=$uboot"
	} > "$log"
	set +e
	(cd "$uboot" && sh -c "$command") >> "$log" 2>&1
	rc=$?
	set -e
	if [ "$rc" -eq 0 ]; then
		echo "openagent-evidence: status=PASS" >> "$log"
	else
		echo "openagent-evidence: status=FAIL rc=$rc" >> "$log"
	fi
	echo "openagent-evidence: ended_utc=$(timestamp_utc)" >> "$log"
	exit "$rc"
}

case "$mode" in
	build)
		if [ -z "${OPENAGENT_UBOOT_CMD:-}" ]; then
			echo "error: set OPENAGENT_UBOOT_CMD to the external U-Boot build command" >&2
			exit 2
		fi
		record_uboot_command \
			u_boot_openagent_build \
			"$evidence_dir/u_boot_openagent_build.log" \
			"$OPENAGENT_UBOOT_CMD"
		;;
	boot-chain)
		if [ -z "${OPENAGENT_UBOOT_BOOT_CMD:-}" ]; then
			echo "error: set OPENAGENT_UBOOT_BOOT_CMD to the external boot-chain command" >&2
			exit 2
		fi
		record_uboot_command \
			u_boot_opensbi_boot_chain \
			"$evidence_dir/u_boot_opensbi_boot_chain.log" \
			"$OPENAGENT_UBOOT_BOOT_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
