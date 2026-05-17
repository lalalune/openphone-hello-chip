#!/bin/bash
# Run OpenLane 2 physical design flow for hello chip (hello_chip_top / sky130A)
# Usage: ./pd/openlane/run.sh [--smoke]
#   --smoke   run the small hello_pd_smoke_top design instead of the full SoC
#
# Prerequisites:
#   pip3 install openlane          (OpenLane 2)
#   pip3 install volare && volare enable --pdk sky130 latest
# OR use the pinned Docker image listed in pd/signoff/manifest.yaml.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%dT%H%M%SZ)

# Config selection
CONFIG="$SCRIPT_DIR/config.sky130.json"
if [ "${1:-}" = "--smoke" ]; then
    CONFIG="$SCRIPT_DIR/config.pd-smoke.sky130.json"
    echo "=== Hello Chip OpenLane 2 — SMOKE run ==="
else
    echo "=== Hello Chip OpenLane 2 — full SoC run ==="
fi

RUN_DIR="$REPO_ROOT/pd/openlane/runs/RUN_$TIMESTAMP"
echo "Config:  $CONFIG"
echo "Run dir: $RUN_DIR"

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
if [ -z "$PDK_ROOT" ]; then
    export PDK_ROOT="$HOME/.volare"
    echo "PDK_ROOT defaulting to $PDK_ROOT"
fi

if [ ! -d "$PDK_ROOT/sky130A" ]; then
    echo "ERROR: SKY130A PDK not found at $PDK_ROOT/sky130A"
    echo "  Install: pip3 install volare && volare enable --pdk sky130 latest"
    exit 2
fi

USE_DOCKER=0
if ! command -v openlane &>/dev/null; then
    if command -v docker &>/dev/null; then
        USE_DOCKER=1
        echo "openlane CLI not found — falling back to Docker"
    else
        echo "ERROR: Neither 'openlane' CLI nor 'docker' found."
        echo "  Install OpenLane 2: pip3 install openlane"
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Launch flow
# ---------------------------------------------------------------------------
mkdir -p "$RUN_DIR"

if [ "$USE_DOCKER" -eq 0 ]; then
    openlane \
        --run-tag "RUN_$TIMESTAMP" \
        --pdk-root "$PDK_ROOT" \
        --pdk sky130A \
        "$CONFIG" 2>&1 | tee "$RUN_DIR/openlane.log"
else
    OPENLANE_IMAGE="ghcr.io/efabless/openlane2:2.4.0.dev1"
    docker run --rm \
        -v "$REPO_ROOT:$REPO_ROOT" \
        -v "$PDK_ROOT:$PDK_ROOT" \
        -e PDK_ROOT="$PDK_ROOT" \
        -w "$REPO_ROOT" \
        "$OPENLANE_IMAGE" \
        openlane \
            --run-tag "RUN_$TIMESTAMP" \
            --pdk-root "$PDK_ROOT" \
            --pdk sky130A \
            "$CONFIG" 2>&1 | tee "$RUN_DIR/openlane.log"
fi

# ---------------------------------------------------------------------------
# Artifact summary
# ---------------------------------------------------------------------------
FINAL_DIR="$REPO_ROOT/pd/openlane/runs/RUN_$TIMESTAMP/final"
echo ""
echo "=== Run complete ==="
if [ -d "$FINAL_DIR" ]; then
    echo "Artifacts in $FINAL_DIR:"
    ls -lh "$FINAL_DIR/gds/"*.gds  2>/dev/null && true || echo "  GDS:     not found"
    ls -lh "$FINAL_DIR/def/"*.def  2>/dev/null && true || echo "  DEF:     not found"
    ls -lh "$FINAL_DIR/spef/"*.spef 2>/dev/null && true || echo "  SPEF:    not found"
    ls -lh "$FINAL_DIR/sdc/"*.sdc  2>/dev/null && true || echo "  SDC:     not found"
    find "$FINAL_DIR" -name "*.v"  2>/dev/null | head -5 || echo "  Netlist: not found"

    # Copy signoff-relevant reports to build/pd/signoff for the manifest checker
    mkdir -p "$REPO_ROOT/build/pd/signoff"
    find "$REPO_ROOT/pd/openlane/runs/RUN_$TIMESTAMP" \
        \( -name "*.drc" -o -name "*.lvs" -o -name "*.rpt" -o -name "*.log" \) \
        -exec cp {} "$REPO_ROOT/build/pd/signoff/" 2>/dev/null \; || true
    echo "Signoff reports mirrored to build/pd/signoff/"
else
    echo "WARNING: No final/ directory found."
    echo "  Check: $RUN_DIR/openlane.log"
    echo "  Check: $RUN_DIR/error.log"
    exit 1
fi

echo ""
echo "Next steps:"
echo "  Manifest check: python3 scripts/check_pd_signoff.py --manifest-only"
echo "  Full signoff:   python3 scripts/check_pd_signoff.py"
