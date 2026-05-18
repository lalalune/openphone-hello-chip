#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
	echo "usage: $0 /path/to/buildroot defconfig|image-manifest|smoke" >&2
	exit 2
fi

buildroot=$1
mode=$2
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../../.." && pwd)
external="$repo_root/sw/buildroot"
evidence_dir="$repo_root/docs/evidence/buildroot"

if [ ! -f "$buildroot/Makefile" ] || [ ! -d "$buildroot/configs" ]; then
	echo "error: $buildroot does not look like a Buildroot checkout" >&2
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
		echo "openphone-evidence: target=buildroot artifact=$artifact"
		echo "openphone-evidence: command=$command"
		started=$(timestamp_utc)
		echo "openphone-evidence: started_utc=$started"
		echo "openphone-evidence: buildroot=$buildroot"
		echo "openphone-evidence: br2_external=$external"
		echo "EXTERNAL_TREE=$buildroot"
		echo "COMMAND=$command"
		echo "START_UTC=$started"
	} > "$log"
	set +e
	(cd "$buildroot" && sh -c "$command") >> "$log" 2>&1
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

case "$mode" in
	defconfig)
		record_command \
			openphone_hello_defconfig \
			"$evidence_dir/openphone_hello_defconfig.log" \
			"make BR2_EXTERNAL=$external openphone_hello_defconfig"
		;;
	image-manifest)
		log="$evidence_dir/openphone_hello_image_manifest.txt"
		images="$buildroot/output/images"
		{
			echo "openphone-evidence: target=buildroot artifact=openphone_hello_image_manifest"
			echo "openphone-evidence: command=find output/images -maxdepth 1 -type f -print -exec sha256sum {} ;"
			started=$(timestamp_utc)
			echo "openphone-evidence: started_utc=$started"
			echo "openphone-evidence: buildroot=$buildroot"
			echo "openphone-evidence: br2_external=$external"
			echo "EXTERNAL_TREE=$buildroot"
			echo "COMMAND=find output/images -maxdepth 1 -type f -print -exec sha256sum {} ;"
			echo "START_UTC=$started"
			} > "$log"
			if [ ! -d "$images" ]; then
				{
					echo "error: missing $images; run the Buildroot image build first"
					echo "openphone-evidence: status=FAIL"
					echo "RESULT=FAIL"
					ended=$(timestamp_utc)
					echo "openphone-evidence: ended_utc=$ended"
					echo "END_UTC=$ended"
				} >> "$log"
				exit 1
			fi
		(
			cd "$buildroot"
			find output/images -maxdepth 1 -type f -print -exec sha256sum {} \;
		) >> "$log" 2>&1
		echo "openphone-evidence: status=PASS" >> "$log"
		echo "RESULT=PASS" >> "$log"
		ended=$(timestamp_utc)
		echo "openphone-evidence: ended_utc=$ended" >> "$log"
		echo "END_UTC=$ended" >> "$log"
		;;
	smoke)
		if [ -z "${HELLO_SMOKE_CMD:-}" ]; then
			echo "error: HELLO_SMOKE_CMD is required, for example: ssh root@TARGET /usr/bin/hello-mmio-smoke" >&2
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
