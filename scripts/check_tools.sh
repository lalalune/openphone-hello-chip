#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
strict=0
if [ "${1:-}" = "--strict" ]; then
    strict=1
fi

if [ -d "$repo_dir/tools/bin" ]; then
    PATH="$repo_dir/tools/bin:$PATH"
fi
if [ -d "$repo_dir/.venv/bin" ]; then
    PATH="$repo_dir/.venv/bin:$PATH"
fi
if [ "$(uname -s)" = "Darwin" ] && [ -d "$repo_dir/external/oss-cad-suite/bin" ]; then
    PATH="$repo_dir/external/oss-cad-suite/bin:$PATH"
fi
if [ "$(uname -s)" = "Darwin" ] && [ -d "/Applications/KiCad/KiCad.app/Contents/MacOS" ]; then
    PATH="/Applications/KiCad/KiCad.app/Contents/MacOS:$PATH"
fi

missing_required=0

check_tool() {
    tool="$1"
    tier="$2"
    gate="$3"
    required="$4"
    if command -v "$tool" >/dev/null 2>&1; then
        printf "%-22s %-12s %-28s %s\n" "$tool" "$tier" "$gate" "$(command -v "$tool")"
    else
        printf "%-22s %-12s %-28s MISSING\n" "$tool" "$tier" "$gate"
        if [ "$required" = "required" ]; then
            missing_required=1
        fi
    fi
}

check_python_package() {
    module="$1"
    dist="$2"
    gate="$3"
    if "$python_bin" - "$module" "$dist" >/dev/null 2>&1 <<'PY'
import importlib.metadata
import sys
module = sys.argv[1]
dist = sys.argv[2]
try:
    __import__(module)
    print(importlib.metadata.version(dist))
except Exception:
    raise SystemExit(1)
PY
    then
        version="$("$python_bin" - "$module" "$dist" <<'PY'
import importlib.metadata
import sys
__import__(sys.argv[1])
print(importlib.metadata.version(sys.argv[2]))
PY
)"
        printf "%-22s %-12s %-28s %s\n" "$dist" "python" "$gate" "$version"
    else
        printf "%-22s %-12s %-28s MISSING\n" "$dist" "python" "$gate"
        missing_required=1
    fi
}

printf "%-22s %-12s %-28s %s\n" "TOOL" "TIER" "GATE" "PATH_OR_STATUS"
printf "%-22s %-12s %-28s %s\n" "----" "----" "----" "--------------"

check_tool python3 fast "repo scripts/docs" required
check_tool pip3 fast ".venv bootstrap" required
check_tool make fast "documented gates" required
check_tool git fast "source/upstream refs" required
check_tool verilator fast "smoke/cocotb/verilator" optional
check_tool yosys fast "synth/formal fallback" optional
check_tool yosys-smtbmc fast "formal fallback" optional
check_tool z3 fast "formal solver" optional
check_tool iverilog fast "optional RTL sims" optional
check_tool qemu-system-riscv64 fast "qemu-check" optional
check_tool docker host "container baseline" optional
check_tool nix host "dev shell/flake" optional
check_tool cmake host "native builds" optional
check_tool ninja host "native builds" optional
check_tool rsync host "external BSP imports" optional
check_tool java host "AOSP builds" optional
check_tool javac host "AOSP builds" optional
check_tool repo heavy "AOSP checkout sync" optional
check_tool adb heavy "Android/Cuttlefish tests" optional
check_tool cvd heavy "Cuttlefish launch" optional
check_tool launch_cvd heavy "legacy Cuttlefish launch" optional
check_tool dtc heavy "Linux devicetree build" optional
check_tool bc heavy "Linux kernel build" optional
check_tool flex heavy "Linux/AOSP builds" optional
check_tool bison heavy "Linux/AOSP builds" optional
check_tool riscv64-unknown-elf-gcc heavy "qemu stub build" optional
check_tool riscv64-linux-gnu-gcc heavy "Linux/Buildroot cross build" optional
check_tool gtkwave host "wave debug" optional
check_tool sby heavy "strict formal" optional
check_tool boolector heavy "legacy formal solver" optional
check_tool openroad heavy "PD implementation" optional
check_tool openlane heavy "PD implementation" optional
check_tool nextpnr-ecp5 heavy "FPGA bitstream" optional
check_tool ecppack heavy "FPGA bitstream" optional
check_tool klayout heavy "layout review/DRC" optional
check_tool magic heavy "layout DRC/LVS" optional
check_tool netgen heavy "LVS" optional
check_tool renode heavy "renode-check" optional
check_tool kicad-cli heavy "board artifacts" optional
check_tool fio heavy "storage benchmarks" optional
check_tool bw_mem heavy "lmbench bandwidth" optional
check_tool lat_mem_rd heavy "lmbench latency" optional
check_tool coremark heavy "CoreMark benchmark" optional
check_tool stream_c.exe heavy "STREAM benchmark" optional
check_tool benchmark_model heavy "TFLite benchmark" optional
check_tool openocd heavy "board debug probes" optional
check_tool sigrok-cli heavy "board signal capture" optional

if [ -x "$repo_dir/.venv/bin/python" ]; then
    python_bin="$repo_dir/.venv/bin/python"
    printf "%-22s %-12s %-28s %s\n" ".venv" "python" "isolated repo env" "$repo_dir/.venv"
else
    python_bin="$(command -v python3)"
    printf "%-22s %-12s %-28s %s\n" ".venv" "python" "isolated repo env" "MISSING"
fi

check_python_package cocotb cocotb "cocotb"
check_python_package pytest pytest "pytest/docs"
check_python_package numpy numpy "runtime/tests"
check_python_package yaml PyYAML "yaml checks"

if [ "$strict" -eq 1 ] && [ "$missing_required" -ne 0 ]; then
    echo "Required fast-path tools or Python packages are missing."
    exit 1
fi
