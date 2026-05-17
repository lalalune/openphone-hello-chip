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
else
    if ! command -v docker >/dev/null 2>&1; then
        echo "OpenLane missing and docker is not on PATH."
        echo "Install OpenLane 2, or install Docker and run: OPENLANE_IMAGE=$IMAGE scripts/install_openlane_image.sh"
        exit 1
    fi
    if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
        echo "OpenLane missing and Docker image is not installed: $IMAGE"
        echo "Install it with: OPENLANE_IMAGE=$IMAGE scripts/install_openlane_image.sh"
        echo "Then rerun: OPENLANE_CONFIG=$CONFIG make openlane"
        exit 1
    fi
    docker run --rm -v "$PWD:/work" -w /work "$IMAGE" openlane "$CONFIG"
fi
