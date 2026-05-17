#!/usr/bin/env bash
# Run the CTS smoke subset against a Cuttlefish riscv64 device.
#
# Fails closed if:
#   - AOSP_TREE is unset or not a built AOSP tree
#   - cts-tradefed is missing
#   - adb does not see exactly one ready device
#
# Modules and filters are defined in docs/android/cts-vts-smoke-plan.md and
# kept in sync here. Do NOT add modules that require camera, cellular, audio,
# Vulkan, biometrics, secure element, or Play services.

set -euo pipefail

die() {
  printf 'run_cts_smoke: %s\n' "$*" >&2
  exit 2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not on PATH: $1"
}

AOSP_TREE="${AOSP_TREE:-}"
ARCHIVE_ROOT="${ARCHIVE_ROOT:-out/cf-riscv64/cts-vts}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${ARCHIVE_ROOT}/${TIMESTAMP}"

[ -n "${AOSP_TREE}" ] || die "AOSP_TREE must point at a built AOSP riscv64 tree"
[ -d "${AOSP_TREE}" ] || die "AOSP_TREE does not exist: ${AOSP_TREE}"
[ -x "${AOSP_TREE}/out/host/linux-x86/cts/android-cts/tools/cts-tradefed" ] \
  || die "cts-tradefed not built under ${AOSP_TREE}/out/host/linux-x86/cts"

require_cmd adb

DEVICES="$(adb devices | awk 'NR>1 && $2=="device" {print $1}')"
COUNT="$(printf '%s\n' "${DEVICES}" | grep -c . || true)"
[ "${COUNT}" = "1" ] \
  || die "expected exactly 1 ready adb device, found ${COUNT}: ${DEVICES}"

mkdir -p "${ARCHIVE}"

{
  echo "timestamp_utc=${TIMESTAMP}"
  echo "aosp_tree=${AOSP_TREE}"
  ( cd "${AOSP_TREE}" && \
    if [ -f build/make/core/build_id.mk ]; then
      grep -E '^BUILD_ID' build/make/core/build_id.mk || true
    fi )
  adb shell getprop ro.build.id
  adb shell getprop ro.product.cpu.abi
  adb shell getprop sys.boot_completed
} > "${ARCHIVE}/build-info.txt"

adb shell getprop > "${ARCHIVE}/device-info.txt" || true

TRADEFED="${AOSP_TREE}/out/host/linux-x86/cts/android-cts/tools/cts-tradefed"

set -x
"${TRADEFED}" run commandAndExit cts \
  --abi riscv64 \
  --module CtsLibcoreTestCases \
  --module CtsBionicTestCases \
  --module CtsJniTestCases \
  --module CtsUtilTestCases \
  --module CtsAppOpsTestCases \
  --module CtsPermissionTestCases \
  --module CtsSelinuxTargetSdkCurrentTestCases \
  --module CtsSecurityTestCases \
    --include-filter "CtsSecurityTestCases android.security.cts.SELinuxTest" \
    --include-filter "CtsSecurityTestCases android.security.cts.FileSystemPermissionTest" \
  --module CtsNetTestCases \
    --include-filter "CtsNetTestCases android.net.cts.SocketTest" \
    --include-filter "CtsNetTestCases android.net.cts.UriTest" \
  --log-level-display info \
  --skip-preconditions \
  2>&1 | tee "${ARCHIVE}/cts-stdout.log"
set +x

RESULTS_DIR="$(ls -td "${AOSP_TREE}"/out/host/linux-x86/cts/android-cts/results/* 2>/dev/null | head -1 || true)"
if [ -n "${RESULTS_DIR}" ]; then
  cp -r "${RESULTS_DIR}" "${ARCHIVE}/cts-results/"
  echo "archived results: ${ARCHIVE}/cts-results/"
else
  echo "WARNING: no tradefed results directory found" >&2
fi

echo "CTS smoke archive: ${ARCHIVE}"
