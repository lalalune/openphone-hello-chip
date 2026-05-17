#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ -d "$repo_dir/tools/bin" ]; then
    PATH="$repo_dir/tools/bin:$PATH"
fi
if [ "$(uname -s)" = "Darwin" ] && [ -d "$repo_dir/external/oss-cad-suite/bin" ]; then
    PATH="$repo_dir/external/oss-cad-suite/bin:$PATH"
fi

tools="docker nix verilator yosys sby openroad openlane klayout magic netgen iverilog gtkwave python3 pip3 make cmake ninja git qemu-system-riscv64 renode kicad-cli"

for tool in $tools; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf "%-24s %s\n" "$tool" "$(command -v "$tool")"
    else
        printf "%-24s MISSING\n" "$tool"
    fi
done
