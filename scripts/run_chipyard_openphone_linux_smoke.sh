#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
checkout="${CHIPYARD_CHECKOUT:-$repo_dir/external/chipyard}"
sim_dir="$checkout/sims/verilator"
out_dir="$repo_dir/build/chipyard/openphone_rocket"
log="$out_dir/verilator-linux-smoke.log"
config="${CHIPYARD_CONFIG:-OpenPhoneRocketConfig}"
config_package="${CHIPYARD_CONFIG_PACKAGE:-openphone}"
binary="${CHIPYARD_LINUX_BINARY:-}"

mkdir -p "$out_dir"

if [ -z "$binary" ]; then
	printf 'STATUS: BLOCKED chipyard.verilator_linux_smoke\n'
	printf '  simulator_path: external/chipyard/sims/verilator\n'
	printf "  next_command: cd external/chipyard/sims/verilator && source ../../env.sh && make CONFIG=%s CONFIG_PACKAGE=%s BINARY=\\$CHIPYARD_LINUX_BINARY LOADMEM=1 run-binary\n" "$config" "$config_package"
	printf '  - CHIPYARD_LINUX_BINARY is unset; provide a real OpenSBI/Linux ELF payload\n'
	exit 2
fi

if [ ! -f "$binary" ]; then
	printf 'STATUS: BLOCKED chipyard.verilator_linux_smoke\n'
	printf '  simulator_path: external/chipyard/sims/verilator\n'
	printf '  - CHIPYARD_LINUX_BINARY does not point to a file: %s\n' "$binary"
	exit 2
fi

cd "$repo_dir"
python3 scripts/check_chipyard_verilator_preflight.py

cd "$sim_dir"
# shellcheck disable=SC1091
. ../../env.sh

set +e
make CONFIG="$config" CONFIG_PACKAGE="$config_package" BINARY="$binary" LOADMEM=1 run-binary >"$log" 2>&1
status=$?
set -e

tail -n 80 "$log"

if [ "$status" -ne 0 ]; then
	printf 'STATUS: BLOCKED chipyard.verilator_linux_smoke\n'
	printf '  simulator_path: external/chipyard/sims/verilator\n'
	printf '  log: build/chipyard/openphone_rocket/verilator-linux-smoke.log\n'
	printf '  - make run-binary exited with status %s\n' "$status"
	exit 2
fi

cd "$repo_dir"
CHIPYARD_LINUX_BINARY="$binary" python3 scripts/check_chipyard_verilator_linux_smoke.py
