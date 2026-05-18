#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
raw_dir="$repo_dir/build/evidence/cpu_ap/raw"
generated_manifest="${OPENPHONE_GENERATED_MANIFEST:-build/chipyard/openphone_rocket/OpenPhoneRocketConfig.manifest.json}"
mode="${1:-all}"

usage() {
	printf 'usage: %s [all|opensbi-boot|linux-boot|trap-timer-irq|isa-cache-mmu|ap-benchmarks]\n' "$0"
	printf '\n'
	printf 'Set one command env var per capture. Each command must run the generated AP simulator/test and print the real transcript to stdout/stderr:\n'
	printf '  OPENPHONE_OPENSBI_BOOT_CMD\n'
	printf '  OPENPHONE_LINUX_BOOT_CMD\n'
	printf '  OPENPHONE_TRAP_TIMER_IRQ_CMD\n'
	printf '  OPENPHONE_ISA_CACHE_MMU_CMD\n'
	printf '  OPENPHONE_AP_BENCHMARKS_CMD\n'
	printf '\n'
	printf 'Optional:\n'
	printf '  OPENPHONE_GENERATED_MANIFEST=%s\n' "$generated_manifest"
	printf '\n'
	printf 'Marker checklist:\n'
	printf '  python3 scripts/capture_cpu_ap_evidence.py template all\n'
}

env_name_for_mode() {
	case "$1" in
		opensbi-boot) printf 'OPENPHONE_OPENSBI_BOOT_CMD' ;;
		linux-boot) printf 'OPENPHONE_LINUX_BOOT_CMD' ;;
		trap-timer-irq) printf 'OPENPHONE_TRAP_TIMER_IRQ_CMD' ;;
		isa-cache-mmu) printf 'OPENPHONE_ISA_CACHE_MMU_CMD' ;;
		ap-benchmarks) printf 'OPENPHONE_AP_BENCHMARKS_CMD' ;;
		*) return 1 ;;
	esac
}

run_mode() {
	capture_mode="$1"
	env_name="$(env_name_for_mode "$capture_mode")"
	command_text="$(eval "printf '%s' \"\${$env_name:-}\"")"
	if [ -z "$command_text" ]; then
		printf 'STATUS: BLOCKED cpu_ap.capture.%s\n' "$capture_mode"
		printf '  - %s is unset\n' "$env_name"
		printf '  - run: python3 scripts/capture_cpu_ap_evidence.py template %s\n' "$capture_mode"
		return 2
	fi

	mkdir -p "$raw_dir"
	raw_log="$raw_dir/${capture_mode}.raw.log"
	printf 'STATUS: RUN cpu_ap.capture.%s\n' "$capture_mode"
	printf '  command_env: %s\n' "$env_name"
	printf '  raw_log: %s\n' "${raw_log#"$repo_dir"/}"

	set +e
	(
		cd "$repo_dir"
		sh -c "$command_text"
	) >"$raw_log" 2>&1
	status=$?
	set -e
	if [ "$status" -ne 0 ]; then
		printf 'STATUS: FAIL cpu_ap.capture.%s\n' "$capture_mode"
		printf '  - command exited with status %s\n' "$status"
		printf '  - raw transcript kept at %s\n' "${raw_log#"$repo_dir"/}"
		return "$status"
	fi

	python3 "$repo_dir/scripts/capture_cpu_ap_evidence.py" intake "$capture_mode" \
		--source "$raw_log" \
		--command "$command_text" \
		--generated-manifest "$generated_manifest"
}

case "$mode" in
	-h|--help)
		usage
		exit 0
		;;
	all)
		run_mode opensbi-boot
		run_mode linux-boot
		run_mode trap-timer-irq
		run_mode isa-cache-mmu
		run_mode ap-benchmarks
		;;
	opensbi-boot|linux-boot|trap-timer-irq|isa-cache-mmu|ap-benchmarks)
		run_mode "$mode"
		;;
	*)
		usage >&2
		exit 2
		;;
esac
