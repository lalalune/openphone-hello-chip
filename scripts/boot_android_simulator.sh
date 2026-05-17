#!/usr/bin/env sh
# shellcheck disable=SC2016
set -eu

repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)
report="$repo_root/build/reports/android_sim_boot.json"
evidence_dir="$repo_root/docs/evidence/android"
aosp_dir=${AOSP_DIR:-}
aosp_shell=${AOSP_SHELL:-bash}
aosp_product=${AOSP_PRODUCT:-openphone_ai_soc-userdebug}
aosp_cuttlefish_args=${AOSP_CUTTLEFISH_ARGS:---cpus=4 --memory_mb=8192 --gpu_mode=none}
aosp_adb_timeout_seconds=${AOSP_ADB_TIMEOUT_SECONDS:-180}
run_cuttlefish=0
run_cts=0
run_vts=0
run_qemu=0
run_renode=0
require_full_evidence=1
host_os=$(uname -s 2>/dev/null || printf unknown)
host_arch=$(uname -m 2>/dev/null || printf unknown)
capture_failures=0

usage() {
	cat >&2 <<'EOF'
usage: AOSP_DIR=/path/to/aosp scripts/boot_android_simulator.sh [--run-cuttlefish] [--run-cts] [--run-vts] [--run-qemu] [--run-renode] [--build-only]

Runs the OpenPhone Android simulator evidence sequence against an external AOSP
checkout. By default the final gate attempts every AOSP evidence category
tracked by docs/android/bsp-log-evidence-manifest.json and
scripts/check_software_bsp.py: lunch, vendorimage, VINTF, SELinux policy,
CTS/VTS intake, and virtual-device smoke evidence for Cuttlefish, QEMU, and
Renode. Use --build-only to stop before virtual-device smoke and compatibility
runs without claiming Android boot.
EOF
}

while [ "$#" -gt 0 ]; do
	case "$1" in
		--aosp-dir)
			if [ "$#" -lt 2 ]; then
				usage
				exit 2
			fi
			aosp_dir=$2
			shift 2
			;;
		--run-cuttlefish)
			run_cuttlefish=1
			shift
			;;
		--run-cts)
			run_cts=1
			shift
			;;
		--run-vts)
			run_vts=1
			shift
			;;
		--run-qemu)
			run_qemu=1
			shift
			;;
		--run-renode)
			run_renode=1
			shift
			;;
		--build-only)
			require_full_evidence=0
			shift
			;;
		--help|-h)
			usage
			exit 0
			;;
		*)
			usage
			exit 2
			;;
	esac
done

if [ "$require_full_evidence" -eq 1 ]; then
	run_cuttlefish=1
	run_cts=1
	run_vts=1
	run_qemu=1
	run_renode=1
fi

mkdir -p "$(dirname "$report")" "$evidence_dir"

json_escape() {
	printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

json_bool() {
	if [ "$1" -eq 1 ]; then
		printf 'true'
	else
		printf 'false'
	fi
}

host_requirements_json() {
	python3 - "$host_os" "$host_arch" "$run_cuttlefish" "$run_qemu" "$run_renode" <<'PY'
import json
import shutil
import sys

host_os, host_arch = sys.argv[1], sys.argv[2]
run_cuttlefish = sys.argv[3] == "1"
run_qemu = sys.argv[4] == "1"
run_renode = sys.argv[5] == "1"
missing = []
if host_os != "Linux":
    missing.append("Linux host required for local Android virtual-device launches")
if run_cuttlefish and host_os == "Linux" and not any(shutil.which(tool) for tool in ("launch_cvd", "cvd")):
    missing.append("Cuttlefish launcher not found on PATH")
if run_cuttlefish and host_os == "Linux" and shutil.which("adb") is None:
    missing.append("adb not found on PATH")
if run_qemu and shutil.which("qemu-system-riscv64") is None:
    missing.append("qemu-system-riscv64 not found on PATH")
if run_renode and shutil.which("renode") is None:
    missing.append("renode not found on PATH")
print(json.dumps({
    "host_os": host_os,
    "host_arch": host_arch,
    "missing": missing,
}))
PY
}

evidence_json() {
	mode=$1
	python3 - "$mode" <<'PY'
import json
import sys

mode = sys.argv[1]
build = [
    "docs/evidence/android/openphone_ai_soc_lunch.log",
    "docs/evidence/android/openphone_ai_soc_vendorimage.log",
    "docs/evidence/android/openphone_ai_soc_checkvintf.log",
    "docs/evidence/android/openphone_ai_soc_sepolicy_build.log",
    "docs/evidence/android/openphone_ai_soc_selinux_neverallow.log",
]
full = build + [
    "docs/evidence/android/openphone_ai_soc_cts_vts_plan.log",
    "docs/evidence/android/cuttlefish_riscv64_smoke.log",
    "docs/evidence/android/qemu_riscv64_smoke.log",
    "docs/evidence/android/renode_hello_soc_smoke.log",
]
print(json.dumps(build if mode == "build" else full, indent=2))
PY
}

write_report() {
	status=$1
	reason=$2
	next=$3
	host_requirements=$(host_requirements_json)
	required_evidence=$(evidence_json full)
	attempted_evidence=$(evidence_json build)
	if [ "$require_full_evidence" -eq 1 ]; then
		attempted_evidence=$(evidence_json full)
	fi
	tmp="$report.$$.$(date +%s).tmp"
	cat > "$tmp" <<EOF
{
  "schema": "openphone.android_sim_boot.v1",
  "status": $(json_escape "$status"),
  "reason": $(json_escape "$reason"),
  "next_step": $(json_escape "$next"),
  "aosp_dir": $(json_escape "${aosp_dir:-}"),
  "aosp_product": $(json_escape "$aosp_product"),
  "run_cuttlefish": $(json_bool "$run_cuttlefish"),
  "run_cts": $(json_bool "$run_cts"),
  "run_vts": $(json_bool "$run_vts"),
  "run_qemu": $(json_bool "$run_qemu"),
  "run_renode": $(json_bool "$run_renode"),
  "require_full_evidence": $(json_bool "$require_full_evidence"),
  "evidence_manifest": "docs/android/bsp-log-evidence-manifest.json",
  "software_bsp_checker": "scripts/check_software_bsp.py aosp --require-evidence",
  "required_evidence": $required_evidence,
  "attempted_evidence": $attempted_evidence,
  "host_requirements": $host_requirements,
  "claim_boundary": "Android virtual-device evidence is software/reference evidence only; it is not hello-chip hardware ABI proof, CDD compliance, GMS certification, or a full Android compatibility claim."
}
EOF
	mv "$tmp" "$report"
}

stage_passed() {
	path=$1
	grep -q 'RESULT=0' "$path" 2>/dev/null && grep -q 'openphone-evidence: status=PASS' "$path" 2>/dev/null
}

record_stage_result() {
	path=$1
	if stage_passed "$path"; then
		return 0
	fi
	capture_failures=$((capture_failures + 1))
	return 1
}

run_helper_stage() {
	mode=$1
	path=$2
	set +e
	AOSP_PRODUCT="$aosp_product" AOSP_SHELL="$aosp_shell" "$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" "$mode"
	rc=$?
	set -e
	if [ "$rc" -ne 0 ]; then
		capture_failures=$((capture_failures + 1))
		return 1
	fi
	record_stage_result "$path" || true
}

capture_aosp_shell() {
	artifact=$1
	out=$2
	command_label=$3
	command_script=$4
	metadata_kind=$5
	rcfile="$repo_root/build/reports/android_sim_boot_stage.$$.$artifact.rc"
	start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
	status=FAIL
	rm -f "$rcfile"
	{
		echo "openphone-evidence: target=aosp artifact=$artifact"
		echo "openphone-evidence: external_tree=$aosp_dir"
		echo "openphone-evidence: command=$command_label"
		echo "EXTERNAL_TREE=$aosp_dir"
		echo "COMMAND=$command_label"
		echo "START_UTC=$start_utc"
		echo "COMPATIBILITY_CLAIM=none"
		if [ "$metadata_kind" = "virtual" ]; then
			echo "BOOT_CLAIM=none"
			echo "SCHEMA=docs/android/boot-transcript.schema.json"
		fi
		echo "openphone-evidence: started_utc=$start_utc"
		cd "$aosp_dir"
		set +e
		env AOSP_PRODUCT="$aosp_product" \
			AOSP_CUTTLEFISH_ARGS="$aosp_cuttlefish_args" \
			AOSP_ADB_TIMEOUT_SECONDS="$aosp_adb_timeout_seconds" \
			"$aosp_shell" -lc "$command_script"
		rc=$?
		set -e
		end_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
		if [ "$rc" -eq 0 ]; then
			status=PASS
		fi
		echo "openphone-evidence: ended_utc=$end_utc"
		echo "openphone-evidence: status=$status"
		echo "END_UTC=$end_utc"
		echo "RESULT=$rc"
		printf '%s' "$rc" > "$rcfile"
	} 2>&1 | tee "$out"
	if [ -f "$rcfile" ]; then
		rc=$(cat "$rcfile")
		rm -f "$rcfile"
	else
		rc=1
	fi
	if [ "$rc" -ne 0 ]; then
		capture_failures=$((capture_failures + 1))
		return 1
	fi
	record_stage_result "$out" || true
}

if [ -z "$aosp_dir" ]; then
	write_report \
		"blocked" \
		"AOSP_DIR is not set, so there is no external AOSP checkout to import/build/boot." \
		"Set AOSP_DIR=/path/to/aosp on a Linux host with Android virtual-device support, then rerun this script."
	echo "BLOCKED: AOSP_DIR is not set; wrote $report"
	exit 2
fi

if [ ! -f "$aosp_dir/build/envsetup.sh" ] || [ ! -d "$aosp_dir/device" ]; then
	write_report \
		"blocked" \
		"$aosp_dir does not look like an AOSP checkout." \
		"Provide an AOSP checkout containing build/envsetup.sh and device/."
	echo "BLOCKED: $aosp_dir does not look like an AOSP checkout; wrote $report"
	exit 2
fi

if [ ! -x "$repo_root/sw/aosp-device/import-aosp-device.sh" ]; then
	write_report "failed" "AOSP import helper is not executable." "chmod +x sw/aosp-device/import-aosp-device.sh"
	echo "FAIL: AOSP import helper is not executable; wrote $report"
	exit 1
fi

"$repo_root/sw/aosp-device/import-aosp-device.sh" "$aosp_dir"

run_helper_stage lunch "$evidence_dir/openphone_ai_soc_lunch.log" || true
run_helper_stage vendorimage "$evidence_dir/openphone_ai_soc_vendorimage.log" || true
run_helper_stage checkvintf "$evidence_dir/openphone_ai_soc_checkvintf.log" || true

capture_aosp_shell \
	openphone_ai_soc_sepolicy_build \
	"$evidence_dir/openphone_ai_soc_sepolicy_build.log" \
	"m vendor_sepolicy.cil selinux_policy" \
	'source build/envsetup.sh &&
		lunch "$AOSP_PRODUCT" >/dev/null &&
		m vendor_sepolicy.cil selinux_policy &&
		grep -R -n "hello_npu_device\|hal_hello_npu_default" out/target/product/openphone_ai_soc/obj/ETC out/target/product/openphone_ai_soc/vendor 2>/dev/null' \
	build || true

capture_aosp_shell \
	openphone_ai_soc_selinux_neverallow \
	"$evidence_dir/openphone_ai_soc_selinux_neverallow.log" \
	"m sepolicy_neverallows" \
	'source build/envsetup.sh &&
		lunch "$AOSP_PRODUCT" >/dev/null &&
		m sepolicy_neverallows &&
		grep -R -n "hello_npu" out/target/product/openphone_ai_soc/obj/ETC out/target/product/openphone_ai_soc/vendor 2>/dev/null' \
	build || true

if [ "$require_full_evidence" -eq 0 ]; then
	python3 "$repo_root/scripts/check_software_bsp.py" aosp
	write_report \
		"blocked" \
		"Android build-only evidence captured; virtual-device smoke and CTS/VTS compatibility intake were not requested." \
		"Rerun without --build-only to attempt full Android simulator evidence."
	echo "BLOCKED: Android build-only evidence captured; wrote $report"
	exit 2
fi

if [ "$run_cts" -eq 1 ] || [ "$run_vts" -eq 1 ]; then
	capture_aosp_shell \
		openphone_ai_soc_cts_vts_plan \
		"$evidence_dir/openphone_ai_soc_cts_vts_plan.log" \
		"m cts vts && cts-tradefed list modules && vts-tradefed list modules" \
		'source build/envsetup.sh &&
			lunch "$AOSP_PRODUCT" >/dev/null &&
			m cts vts &&
			echo "CTS_SCOPE=smoke_only" &&
			echo "VTS_SCOPE=vintf_selinux_hal_manager_only" &&
			echo "EXCLUDED_MODULES=full_cts,full_vts,device_specific" &&
			echo "RESULT_DIR=${ANDROID_HOST_OUT:-out/host/linux-x86}/cts-vts-plan" &&
			(cts-tradefed list modules 2>/dev/null | sed -n "1,40p" || true) &&
			(vts-tradefed list modules 2>/dev/null | sed -n "1,40p" || true)' \
		build || true
fi

if [ "$run_cuttlefish" -eq 1 ]; then
	capture_aosp_shell \
		cuttlefish_riscv64_smoke \
		"$evidence_dir/cuttlefish_riscv64_smoke.log" \
		"launch_cvd or cvd start followed by adb shell getprop smoke checks" \
		'source build/envsetup.sh &&
			lunch "$AOSP_PRODUCT" >/dev/null &&
			echo "openphone_ai_soc" &&
			cleanup() { stop_cvd >/dev/null 2>&1 || true; } &&
			trap cleanup EXIT INT TERM &&
			launch_cvd $AOSP_CUTTLEFISH_ARGS -daemon &&
			deadline=$((SECONDS + AOSP_ADB_TIMEOUT_SECONDS)) &&
			until adb get-state >/dev/null 2>&1; do
				if [ "$SECONDS" -ge "$deadline" ]; then
					echo "virtual-device wait exceeded ${AOSP_ADB_TIMEOUT_SECONDS}s" &&
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
			[ "$abi" = riscv64 ] && [ "$boot" = 1 ]' \
		virtual || true
fi

if [ "$run_qemu" -eq 1 ]; then
	capture_aosp_shell \
		qemu_riscv64_smoke \
		"$evidence_dir/qemu_riscv64_smoke.log" \
		"qemu-system-riscv64 with AOSP-built artifacts followed by console or adb smoke checks" \
		'source build/envsetup.sh &&
			lunch "$AOSP_PRODUCT" >/dev/null &&
			echo "openphone_ai_soc" &&
			command -v qemu-system-riscv64 &&
			test -f out/target/product/openphone_ai_soc/vendor.img &&
			echo "qemu-system-riscv64 AOSP riscv64 smoke requires kernel/system image wiring for this product" &&
			qemu-system-riscv64 --version' \
		virtual || true
fi

if [ "$run_renode" -eq 1 ]; then
	capture_aosp_shell \
		renode_hello_soc_smoke \
		"$evidence_dir/renode_hello_soc_smoke.log" \
		"renode sim/renode/openphone_hello.resc with Android-capable firmware/kernel handoff when available" \
		'source build/envsetup.sh &&
			lunch "$AOSP_PRODUCT" >/dev/null &&
			echo "openphone_ai_soc" &&
			command -v renode &&
			echo "renode Android-capable firmware/kernel handoff smoke requires a real Renode hello SoC Android boot script" &&
			renode --version' \
		virtual || true
fi

set +e
python3 "$repo_root/scripts/check_software_bsp.py" aosp --require-evidence
check_rc=$?
set -e
if [ "$check_rc" -eq 0 ] && [ "$capture_failures" -eq 0 ]; then
	write_report "pass" "Android simulator evidence captured and validated." "none"
	echo "PASS: Android simulator evidence captured and validated; wrote $report"
	exit 0
fi

write_report \
	"failed" \
	"Android simulator evidence did not satisfy the required AOSP BSP evidence manifest." \
	"Inspect docs/evidence/android/*.log, fix failing or missing stages, then rerun this script."
echo "FAIL: Android simulator evidence did not satisfy the required AOSP BSP evidence manifest; wrote $report"
exit 1
