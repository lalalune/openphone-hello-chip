#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
	echo "usage: $0 /path/to/buildroot" >&2
	exit 2
fi

buildroot=$1
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../../.." && pwd)
external="$repo_root/sw/buildroot"

if [ ! -f "$buildroot/Makefile" ] || [ ! -d "$buildroot/configs" ]; then
	echo "error: $buildroot does not look like a Buildroot checkout" >&2
	exit 1
fi

if [ ! -f "$external/external.desc" ] || [ ! -f "$external/Config.in" ] || [ ! -f "$external/external.mk" ]; then
	echo "error: missing BR2_EXTERNAL metadata under $external" >&2
	exit 1
fi

printf 'Run from the Buildroot checkout:\n'
printf '  make BR2_EXTERNAL=%s openphone_hello_defconfig\n' "$external"
printf '  make BR2_EXTERNAL=%s\n' "$external"
