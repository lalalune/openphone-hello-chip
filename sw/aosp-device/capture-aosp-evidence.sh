#!/usr/bin/env sh
set -eu

usage() {
	echo "usage: $0 /path/to/aosp {lunch|vendorimage|checkvintf|cuttlefish-boot|cts-subset|vts-subset}" >&2
}

if [ "$#" -ne 2 ]; then
	usage
	exit 2
fi

aosp=$1
mode=$2
repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/../.." && pwd)
evidence_dir="$repo_root/docs/evidence/android"
aosp_shell=${AOSP_SHELL:-bash}
aosp_product=${AOSP_PRODUCT:-openphone_ai_soc-userdebug}
aosp_cuttlefish_args=${AOSP_CUTTLEFISH_ARGS:---cpus=4 --memory_mb=8192 --gpu_mode=none}
aosp_adb_timeout_seconds=${AOSP_ADB_TIMEOUT_SECONDS:-180}
reference_only_boundary=reference_only_not_hello_chip_ap_evidence

if [ ! -f "$aosp/build/envsetup.sh" ] || [ ! -d "$aosp/device" ]; then
	echo "error: $aosp does not look like an AOSP checkout" >&2
	exit 1
fi
if ! command -v "$aosp_shell" >/dev/null 2>&1; then
	echo "error: AOSP shell '$aosp_shell' is not available; set AOSP_SHELL=/path/to/bash" >&2
	exit 1
fi

mkdir -p "$evidence_dir"

run_capture() {
	artifact=$1
	out=$2
	command_label=$3
	shift 3
	start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
	status=FAIL
	{
		echo "openphone-evidence: target=aosp artifact=$artifact"
		echo "openphone-evidence: external_tree=$aosp"
		echo "openphone-evidence: command=$command_label"
		case "$artifact" in
			cuttlefish_riscv64_boot|cts_virtual_device_subset|vts_virtual_device_subset)
				echo "openphone-evidence: claim_boundary=$reference_only_boundary"
				;;
		esac
		echo "openphone-evidence: started_utc=$start_utc"
		cd "$aosp"
		set +e
		"$@"
		rc=$?
		set -e
		end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
		if [ "$rc" -eq 0 ]; then
			status=PASS
		fi
		echo "openphone-evidence: ended_utc=$end_utc"
		echo "openphone-evidence: status=$status"
		exit "$rc"
	} 2>&1 | tee "$out"
}

case "$mode" in
	lunch)
		run_capture \
			openphone_ai_soc_lunch \
			"$evidence_dir/openphone_ai_soc_lunch.log" \
			"lunch openphone_ai_soc-userdebug" \
			"$aosp_shell" -lc 'source build/envsetup.sh && lunch openphone_ai_soc-userdebug'
		;;
	vendorimage)
		run_capture \
			openphone_ai_soc_vendorimage \
			"$evidence_dir/openphone_ai_soc_vendorimage.log" \
			"m vendorimage" \
			"$aosp_shell" -lc 'source build/envsetup.sh && lunch openphone_ai_soc-userdebug >/dev/null && m vendorimage && find out/target/product/openphone_ai_soc -maxdepth 2 \( -name vendor.img -o -name installed-files-vendor.txt \) -print'
		;;
	checkvintf)
		run_capture \
			openphone_ai_soc_checkvintf \
			"$evidence_dir/openphone_ai_soc_checkvintf.log" \
			"checkvintf openphone_ai_soc" \
			"$aosp_shell" -lc 'source build/envsetup.sh && lunch openphone_ai_soc-userdebug >/dev/null && checkvintf --check-one --dirmap /vendor:out/target/product/openphone_ai_soc/vendor'
		;;
	cuttlefish-boot)
		# shellcheck disable=SC2016
		run_capture \
			cuttlefish_riscv64_boot \
			"$evidence_dir/cuttlefish_riscv64_boot.log" \
			"source build/envsetup.sh && lunch $aosp_product && launch_cvd $aosp_cuttlefish_args -daemon" \
			env AOSP_PRODUCT="$aosp_product" AOSP_CUTTLEFISH_ARGS="$aosp_cuttlefish_args" "$aosp_shell" -lc '
				source build/envsetup.sh &&
				lunch "$AOSP_PRODUCT" >/dev/null &&
				cleanup() { stop_cvd >/dev/null 2>&1 || true; } &&
				trap cleanup EXIT INT TERM &&
				launch_cvd $AOSP_CUTTLEFISH_ARGS -daemon &&
				deadline=$((SECONDS + '"$aosp_adb_timeout_seconds"')) &&
				until adb get-state >/dev/null 2>&1; do
					if [ "$SECONDS" -ge "$deadline" ]; then
						echo "openphone-evidence: adb_wait_timeout_seconds='"$aosp_adb_timeout_seconds"'" &&
						exit 1
					fi
					sleep 2
				done &&
				echo "adb shell true" &&
				adb shell true &&
				echo "adb shell getprop ro.product.cpu.abi" &&
				abi=$(adb shell getprop ro.product.cpu.abi | tr -d "\r") &&
				echo "ro.product.cpu.abi=$abi" &&
				echo "adb shell getprop sys.boot_completed" &&
				boot= &&
				while [ "$SECONDS" -lt "$deadline" ]; do
					boot=$(adb shell getprop sys.boot_completed | tr -d "\r") &&
					[ "$boot" = 1 ] && break
					sleep 2
				done &&
				echo "sys.boot_completed=$boot" &&
				mkdir -p out &&
				adb shell logcat -d -b all > out/openphone-cuttlefish-boot-logcat.txt 2>/dev/null || true
				[ "$abi" = riscv64 ] && [ "$boot" = 1 ]
			'
		;;
	cts-subset)
		run_capture \
			cts_virtual_device_subset \
			"$evidence_dir/cts_virtual_device_subset.log" \
			"cts-tradefed run commandAndExit cts-virtual-device-subset" \
			"$aosp_shell" -lc 'echo "openphone-evidence: compatibility_scope=virtual_device_subset"; cts-tradefed run commandAndExit cts --module CtsOsTestCases --test android.os.cts.BuildTest'
		;;
	vts-subset)
		run_capture \
			vts_virtual_device_subset \
			"$evidence_dir/vts_virtual_device_subset.log" \
			"vts-tradefed run commandAndExit vts-virtual-device-subset" \
			"$aosp_shell" -lc 'echo "openphone-evidence: compatibility_scope=virtual_device_subset"; vts-tradefed run commandAndExit vts --module VtsTrebleVintfTest'
		;;
	*)
		usage
		exit 2
		;;
esac
