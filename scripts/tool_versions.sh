#!/usr/bin/env sh
set -eu

repo_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
mkdir -p "$repo_dir/build/reports"

{
    date -u +"timestamp_utc=%Y-%m-%dT%H:%M:%SZ"
    printf "repo_dir=%s\n" "$repo_dir"
    for tool in docker nix verilator yosys sby openroad openlane klayout magic netgen iverilog python3 make qemu-system-riscv64 renode kicad-cli; do
        if command -v "$tool" >/dev/null 2>&1; then
            printf "%s_path=%s\n" "$tool" "$(command -v "$tool")"
            "$tool" --version 2>&1 | sed "s/^/${tool}_version=/" | head -n 1 || true
        else
            printf "%s_path=MISSING\n" "$tool"
        fi
    done
} > "$repo_dir/build/reports/tool_versions.txt"

echo "Tool versions: build/reports/tool_versions.txt"
