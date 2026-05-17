#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)
report="$repo_root/build/reports/android_sim_boot.json"
aosp_dir=${AOSP_DIR:-}
run_cuttlefish=0
run_cts=0
run_vts=0
require_full_evidence=1
host_os=$(uname -s 2>/dev/null || printf unknown)
host_arch=$(uname -m 2>/dev/null || printf unknown)

usage() {
	cat >&2 <<'EOF'
usage: AOSP_DIR=/path/to/aosp scripts/boot_android_simulator.sh [--run-cuttlefish] [--run-cts] [--run-vts] [--build-only]

Runs the OpenPhone Android simulator boot sequence against an external AOSP
checkout. By default the final gate requires full Android simulator evidence:
lunch, vendorimage, VINTF, Cuttlefish boot, CTS subset, and VTS subset. Use
--build-only to stop after lunch/vendorimage/VINTF validation without claiming
Android boot.
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

mkdir -p "$(dirname "$report")"

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
	python3 - "$host_os" "$host_arch" <<'PY'
import json
import shutil
import sys

host_os, host_arch = sys.argv[1], sys.argv[2]
missing = []
if host_os != "Linux":
    missing.append("Linux host required for local Cuttlefish/KVM launch")
if host_os == "Linux" and not any(shutil.which(tool) for tool in ("launch_cvd", "cvd")):
    missing.append("Cuttlefish launcher not found on PATH")
if host_os == "Linux" and shutil.which("adb") is None:
    missing.append("adb not found on PATH")
print(json.dumps({
    "host_os": host_os,
    "host_arch": host_arch,
    "missing": missing,
}))
PY
}

write_report() {
	status=$1
	reason=$2
	next=$3
	host_requirements=$(host_requirements_json)
	tmp="$report.$$.$(date +%s).tmp"
	cat > "$tmp" <<EOF
{
  "schema": "openphone.android_sim_boot.v1",
  "status": $(json_escape "$status"),
  "reason": $(json_escape "$reason"),
  "next_step": $(json_escape "$next"),
  "aosp_dir": $(json_escape "${aosp_dir:-}"),
  "run_cuttlefish": $(json_bool "$run_cuttlefish"),
  "run_cts": $(json_bool "$run_cts"),
  "run_vts": $(json_bool "$run_vts"),
  "require_full_evidence": $(json_bool "$require_full_evidence"),
  "host_requirements": $host_requirements,
  "claim_boundary": "Cuttlefish/qemu-virt evidence is Android userspace evidence only; it is not hello-chip hardware ABI proof."
}
EOF
	mv "$tmp" "$report"
}

if [ -z "$aosp_dir" ]; then
	write_report \
		"blocked" \
		"AOSP_DIR is not set, so there is no external AOSP checkout to import/build/boot." \
		"Set AOSP_DIR=/path/to/aosp on a Linux host with Cuttlefish support, then rerun this script."
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
"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" lunch
"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" vendorimage
"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" checkvintf

if [ "$run_cuttlefish" -eq 1 ]; then
	"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" cuttlefish-boot
fi

if [ "$run_cts" -eq 1 ]; then
	"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" cts-subset
fi

if [ "$run_vts" -eq 1 ]; then
	"$repo_root/sw/aosp-device/capture-aosp-evidence.sh" "$aosp_dir" vts-subset
fi

if [ "$require_full_evidence" -eq 1 ]; then
	python3 "$repo_root/scripts/check_software_bsp.py" aosp --require-evidence
	write_report "pass" "Android simulator evidence captured and validated." "none"
	echo "PASS: Android simulator evidence captured and validated; wrote $report"
else
	python3 "$repo_root/scripts/check_software_bsp.py" aosp
	write_report \
		"blocked" \
		"Android build-only evidence captured; full boot/CTS/VTS evidence was not requested." \
		"Rerun with --run-cuttlefish --run-cts --run-vts to attempt full Android simulator evidence."
	echo "BLOCKED: Android build-only evidence captured; wrote $report"
	exit 2
fi
