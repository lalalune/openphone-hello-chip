#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 /path/to/opensbi build|handoff" >&2
	exit 2
fi

opensbi=$1
mode=$2
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../.." && pwd)
evidence_dir="$repo_root/docs/evidence/linux"

if [ ! -f "$opensbi/Makefile" ] || [ ! -d "$opensbi/lib" ]; then
	echo "error: $opensbi does not look like an OpenSBI checkout" >&2
	exit 1
fi

mkdir -p "$evidence_dir"

timestamp_utc() {
	date -u '+%Y-%m-%dT%H:%M:%SZ'
}

record_opensbi_command() {
	artifact=$1
	log=$2
	command=$3
	{
		echo "openphone-evidence: target=opensbi artifact=$artifact"
		echo "openphone-evidence: command=$command"
		echo "openphone-evidence: started_utc=$(timestamp_utc)"
		echo "openphone-evidence: opensbi=$opensbi"
	} > "$log"
	set +e
	(cd "$opensbi" && sh -c "$command") >> "$log" 2>&1
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
		record_opensbi_command \
			opensbi_openphone_build \
			"$evidence_dir/opensbi_openphone_build.log" \
			"${OPENPHONE_OPENSBI_CMD:-make PLATFORM=generic FW_DYNAMIC=y}"
		;;
	handoff)
		if [ -z "${OPENPHONE_OPENSBI_HANDOFF_CMD:-}" ]; then
			echo "error: set OPENPHONE_OPENSBI_HANDOFF_CMD to the external boot command" >&2
			exit 2
		fi
		record_opensbi_command \
			opensbi_fw_dynamic_handoff \
			"$evidence_dir/opensbi_fw_dynamic_handoff.log" \
			"$OPENPHONE_OPENSBI_HANDOFF_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
