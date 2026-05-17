#!/usr/bin/env sh
set -eu

CONFIG="${OPENLANE_CONFIG:-pd/openlane/config.sky130.json}"
IMAGE="${OPENLANE_IMAGE:-ghcr.io/efabless/openlane2:2.4.0.dev1}"

if command -v openlane >/dev/null 2>&1; then
    openlane "$CONFIG"
elif command -v flow.tcl >/dev/null 2>&1; then
    case "$CONFIG" in
        */config.json|config.json)
            flow.tcl -design pd/openlane
            ;;
        *)
            echo "Legacy flow.tcl cannot select $CONFIG reliably. Use OpenLane 2 or set OPENLANE_CONFIG=pd/openlane/config.json."
            exit 1
            ;;
    esac
elif command -v docker >/dev/null 2>&1 && docker image inspect "$IMAGE" >/dev/null 2>&1; then
    docker run --rm -v "$PWD:/work" -w /work "$IMAGE" openlane "$CONFIG"
else
    echo "OpenLane missing. Install/pull $IMAGE and rerun with OPENLANE_CONFIG=$CONFIG."
    exit 1
fi
