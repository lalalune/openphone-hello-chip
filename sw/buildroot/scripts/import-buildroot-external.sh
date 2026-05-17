#!/usr/bin/env sh
set -eu

check_only=0

if [ "${1:-}" = "--check" ]; then
	check_only=1
	shift
fi

if [ "$#" -ne 1 ]; then
	echo "usage: $0 [--check] /path/to/buildroot" >&2
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
printf 'Capture real evidence back in this repository:\n'
# shellcheck disable=SC2016
printf '  { printf "EXTERNAL_TREE=%s\\nCOMMAND=make BR2_EXTERNAL=%s openphone_hello_defconfig\\nSTART_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\n"; make BR2_EXTERNAL=%s openphone_hello_defconfig; rc=$?; printf "END_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\nRESULT=$rc\\n"; exit $rc; } 2>&1 | tee %s/docs/evidence/buildroot/openphone_hello_defconfig.log\n' "$buildroot" "$external" "$external" "$repo_root"
# shellcheck disable=SC2016
printf '  { printf "EXTERNAL_TREE=%s\\nCOMMAND=find output/images -maxdepth 1 -type f -print\\nSTART_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\n"; find output/images -maxdepth 1 -type f -print; rc=$?; printf "END_UTC=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)\\nRESULT=$rc\\n"; exit $rc; } 2>&1 | tee %s/docs/evidence/buildroot/openphone_hello_image_manifest.txt\n' "$buildroot" "$repo_root"

if [ "$check_only" -eq 1 ]; then
	missing=0
	for path in \
		"$external/configs/openphone_hello_defconfig" \
		"$external/board/openphone/hello/linux.fragment" \
		"$external/board/openphone/hello/rootfs_overlay/usr/bin/hello-mmio-smoke"; do
		if [ ! -f "$path" ]; then
				echo "FAIL: missing repo artifact ${path#"$repo_root"/}" >&2
			missing=1
		fi
	done
	if [ ! -f "$external/../linux-external.tar.xz" ]; then
		echo "STATUS: BLOCKED buildroot.import-check - missing external kernel tarball ${external#"$repo_root"/}/../linux-external.tar.xz"
		exit 2
	fi
	if [ "$missing" -ne 0 ]; then
		exit 1
	fi
	echo "STATUS: PASS buildroot.import-check - external Buildroot checkout shape, BR2_EXTERNAL inputs, and kernel tarball are present"
	echo "STATUS: BLOCKED buildroot.runtime-evidence - run external Buildroot build and archive docs/evidence/buildroot/*.log"
fi
