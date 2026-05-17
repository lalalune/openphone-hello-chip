#!/usr/bin/env sh
set -eu

if ! command -v make >/dev/null 2>&1; then
    echo "make is required for cocotb"
    exit 1
fi

REPO_ROOT="$(CDPATH=; cd -- "$(dirname "$0")/.." && pwd)"

if [ -n "${PYTHON:-}" ]; then
    PYTHON_BIN="$PYTHON"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
else
    PYTHON_BIN=python3
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN=python3
fi
PYTHON_DIR="$(CDPATH=; cd -- "$(dirname "$PYTHON_BIN")" && pwd)"
if [ -x "$PYTHON_DIR/cocotb-config" ]; then
    PATH="$PYTHON_DIR:$PATH"
fi
PYTHON_SITE="$("$PYTHON_BIN" - <<'PY'
import site
paths = []
for value in site.getsitepackages():
    if value:
        paths.append(value)
user = site.getusersitepackages()
if user:
    paths.append(user)
print(":".join(dict.fromkeys(paths)))
PY
)"
PYTHONPATH="$PYTHON_SITE${PYTHONPATH:+:$PYTHONPATH}"
export PATH PYTHONPATH
PYTHON_PREFIX="$(CDPATH=; cd -- "$PYTHON_DIR/.." && pwd)"
if [ -d "$PYTHON_PREFIX/lib" ]; then
    DYLD_LIBRARY_PATH="$PYTHON_PREFIX/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
    LD_LIBRARY_PATH="$PYTHON_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    export DYLD_LIBRARY_PATH LD_LIBRARY_PATH
fi

if ! "$PYTHON_BIN" -c "import cocotb" >/dev/null 2>&1; then
    if ! python3 -c "import cocotb" >/dev/null 2>&1; then
        echo "cocotb is not installed. Use Docker/Nix or install cocotb in a virtualenv."
        exit 1
    fi
fi

COCOTB_TOP="${COCOTB_TOPLEVEL:-hello_chip_top}"
COCOTB_MOD="${COCOTB_MODULE:-test_hello_chip}"
COCOTB_BUILD="$REPO_ROOT/build/cocotb/${COCOTB_TOP}_${COCOTB_MOD}"
COCOTB_LOCK="$REPO_ROOT/build/cocotb/.${COCOTB_TOP}_${COCOTB_MOD}.lock"
COCOTB_RESULTS_LOCK="$REPO_ROOT/build/cocotb/.results.lock"
COCOTB_ARCHIVE_NAME="${COCOTB_TOP}_${COCOTB_MOD}"
mkdir -p "$REPO_ROOT/build/cocotb"

while ! mkdir "$COCOTB_LOCK" 2>/dev/null; do
    sleep 1
done
while ! mkdir "$COCOTB_RESULTS_LOCK" 2>/dev/null; do
    sleep 1
done
trap 'rmdir "$COCOTB_RESULTS_LOCK" "$COCOTB_LOCK" 2>/dev/null || true' EXIT INT TERM

rm -rf "$COCOTB_BUILD" verify/cocotb/results.xml

if command -v verilator >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=verilator \
        MODULE="$COCOTB_MOD" \
        TOPLEVEL="$COCOTB_TOP" \
        SIM_BUILD="$COCOTB_BUILD"
elif command -v iverilog >/dev/null 2>&1; then
    $(command -v make) -C verify/cocotb SIM=icarus \
        MODULE="$COCOTB_MOD" \
        TOPLEVEL="$COCOTB_TOP" \
        SIM_BUILD="$COCOTB_BUILD"
else
    echo "No cocotb simulator found. Install Verilator or Icarus Verilog."
    exit 1
fi

"$PYTHON_BIN" scripts/check_cocotb_results.py \
    --archive-name "$COCOTB_ARCHIVE_NAME" \
    --top "$COCOTB_TOP" \
    --module "$COCOTB_MOD"
