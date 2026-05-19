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
		echo "openagent-evidence: target=opensbi artifact=$artifact"
		echo "openagent-evidence: command=$command"
		echo "openagent-evidence: started_utc=$(timestamp_utc)"
		echo "openagent-evidence: opensbi=$opensbi"
	} > "$log"
	set +e
	(cd "$opensbi" && sh -c "$command") >> "$log" 2>&1
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
		record_opensbi_command \
			opensbi_openagent_build \
			"$evidence_dir/opensbi_openagent_build.log" \
			"${OPENAGENT_OPENSBI_CMD:-make PLATFORM=generic FW_DYNAMIC=y}"
		;;
	handoff)
		if [ -z "${OPENAGENT_OPENSBI_HANDOFF_CMD:-}" ]; then
			echo "error: set OPENAGENT_OPENSBI_HANDOFF_CMD to the external boot command" >&2
			exit 2
		fi
		record_opensbi_command \
			opensbi_fw_dynamic_handoff \
			"$evidence_dir/opensbi_fw_dynamic_handoff.log" \
			"$OPENAGENT_OPENSBI_HANDOFF_CMD"
		;;
	*)
		echo "error: unknown mode $mode" >&2
		exit 2
		;;
esac
