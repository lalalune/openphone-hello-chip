#!/usr/bin/env sh
set -eu

if ! command -v make >/dev/null 2>&1; then
    echo "make is required for cocotb"
    exit 1
fi

PYTHON_BIN="${PYTHON:-python3}"

if ! "$PYTHON_BIN" -c "import cocotb" >/dev/null 2>&1; then
    if ! python3 -c "import cocotb" >/dev/null 2>&1; then
        echo "cocotb is not installed. Use Docker/Nix or install cocotb in a virtualenv."
        exit 1
    fi
fi

rm -rf verify/cocotb/sim_build verify/cocotb/results.xml

if command -v verilator >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=verilator \
        MODULE="${COCOTB_MODULE:-test_hello_chip}" \
        TOPLEVEL="${COCOTB_TOPLEVEL:-hello_chip_top}"
elif command -v iverilog >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=icarus \
        MODULE="${COCOTB_MODULE:-test_hello_chip}" \
        TOPLEVEL="${COCOTB_TOPLEVEL:-hello_chip_top}"
else
    echo "No cocotb simulator found. Install Verilator or Icarus Verilog."
    exit 1
fi

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import re
import sys

path = Path("verify/cocotb/results.xml")
if not path.is_file():
    raise SystemExit("verify/cocotb/results.xml missing after cocotb run")

text = path.read_text(errors="ignore")
failures = sum(int(value) for value in re.findall(r'failures="(\d+)"', text))
errors = sum(int(value) for value in re.findall(r'errors="(\d+)"', text))
failure_elements = len(re.findall(r"<failure\b", text))
error_elements = len(re.findall(r"<error\b", text))
testcases = len(re.findall(r"<testcase\b", text))

if failures or errors or failure_elements or error_elements or not testcases:
    print(
        "cocotb XML indicates failure: "
        f"testcases={testcases} failures={failures + failure_elements} errors={errors + error_elements}"
    )
    sys.exit(1)
PY
