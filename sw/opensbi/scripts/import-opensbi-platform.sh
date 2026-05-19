#!/usr/bin/env sh
set -eu

check_only=0

if [ "${1:-}" = "--check" ]; then
	check_only=1
	shift
fi

if [ "$#" -ne 1 ]; then
	echo "usage: $0 [--check] /path/to/opensbi" >&2
	exit 2
fi

opensbi=$1
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../../.." && pwd)
platform="$repo_root/sw/opensbi/platform/openagent"

if [ ! -f "$opensbi/Makefile" ] || [ ! -d "$opensbi/lib" ] || [ ! -d "$opensbi/platform" ]; then
	echo "error: $opensbi does not look like an OpenSBI checkout" >&2
	exit 1
fi

for path in "$platform/config.mk" "$platform/objects.mk" "$platform/platform.c"; do
	if [ ! -f "$path" ]; then
		echo "error: missing repo OpenSBI platform artifact ${path#"$repo_root"/}" >&2
		exit 1
	fi
done

printf 'Import commands:\n'
printf '  mkdir -p %s/platform/openagent\n' "$opensbi"
printf '  cp -R %s/. %s/platform/openagent/\n' "$platform" "$opensbi"
printf 'Capture real evidence back in this repository:\n'
printf '  OPENAGENT_OPENSBI_CMD='\''make PLATFORM=openagent FW_PAYLOAD_PATH=/path/to/Image FW_PAYLOAD_FDT_PATH=/path/to/openagent-e1.dtb'\'' %s/docs/sw/opensbi/capture-opensbi-evidence.sh %s build\n' "$repo_root" "$opensbi"
printf '  OPENAGENT_OPENSBI_HANDOFF_CMD='\''/exact/qemu-or-renode fw_dynamic handoff command'\'' %s/docs/sw/opensbi/capture-opensbi-evidence.sh %s handoff\n' "$repo_root" "$opensbi"

if [ "$check_only" -eq 1 ]; then
	if [ ! -f "$opensbi/platform/openagent/config.mk" ]; then
		echo "STATUS: BLOCKED opensbi.import-check - missing imported platform/openagent/config.mk"
		exit 2
	fi
	echo "STATUS: PASS opensbi.import-check - external OpenSBI checkout shape and OpenAgent platform import are present"
	echo "STATUS: BLOCKED opensbi.runtime-evidence - run external OpenSBI build and fw_dynamic handoff capture"
	exit 0
fi

mkdir -p "$opensbi/platform/openagent"
cp -R "$platform"/. "$opensbi/platform/openagent/"
printf 'Imported OpenAgent OpenSBI platform files into the external OpenSBI tree.\n'
