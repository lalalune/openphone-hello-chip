#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
	echo "usage: $0 /path/to/aosp" >&2
	exit 2
fi

aosp=$1
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
device_src="$repo_root/sw/aosp-device/device/openphone/openphone_ai_soc"
device_dst="$aosp/device/openphone/openphone_ai_soc"

if [ ! -f "$aosp/build/envsetup.sh" ] || [ ! -d "$aosp/device" ]; then
	echo "error: $aosp does not look like an AOSP checkout" >&2
	exit 1
fi

mkdir -p "$aosp/device/openphone"
rsync -a --delete "$device_src/" "$device_dst/"

printf 'Imported OpenPhone AOSP device tree.\n'
printf 'Validate from the AOSP checkout:\n'
printf '  source build/envsetup.sh\n'
printf '  lunch openphone_ai_soc-userdebug\n'
printf '  m nothing\n'
