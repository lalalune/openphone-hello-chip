#!/usr/bin/env sh
set -eu

CONFIG="${OPENLANE_CONFIG:-pd/openlane/config.sky130.json}"
IMAGE="${OPENLANE_IMAGE:-ghcr.io/efabless/openlane2:2.4.0.dev1}"
TIMEOUT_SECONDS="${OPENLANE_TIMEOUT_SECONDS:-}"
REPO_DIR="$(CDPATH=; cd -- "$(dirname -- "$0")/.." && pwd)"
PDK_ROOT_HOST="${PDK_ROOT:-$REPO_DIR/external/pdks}"
LOCK_DIR="$REPO_DIR/.openlane-run.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    if [ -f "$LOCK_DIR/pid" ] && kill -0 "$(cat "$LOCK_DIR/pid")" 2>/dev/null; then
        echo "OpenLane run already active under pid $(cat "$LOCK_DIR/pid")."
        echo "Remove $LOCK_DIR only after confirming no OpenLane/Docker flow is running."
        exit 3
    fi
    echo "Removing stale OpenLane lock: $LOCK_DIR"
    rm -rf "$LOCK_DIR"
    mkdir "$LOCK_DIR"
fi
printf '%s\n' "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

run_maybe_timeout() {
    if [ -n "$TIMEOUT_SECONDS" ]; then
        python3 "$REPO_DIR/scripts/run_with_timeout.py" \
            --timeout-seconds "$TIMEOUT_SECONDS" \
            --label openlane \
            -- "$@"
    else
        "$@"
    fi
}

if command -v openlane >/dev/null 2>&1; then
    run_maybe_timeout openlane "$CONFIG"
elif command -v flow.tcl >/dev/null 2>&1; then
    case "$CONFIG" in
        */config.json|config.json)
            run_maybe_timeout flow.tcl -design pd/openlane
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
    case "$PDK_ROOT_HOST" in
        "$REPO_DIR"/external/pdks) pdk_root_container="/work/external/pdks" ;;
        *) pdk_root_container="$PDK_ROOT_HOST" ;;
    esac
    run_maybe_timeout docker run --rm -v "$PWD:/work" -w /work -e "PDK_ROOT=$pdk_root_container" "$IMAGE" openlane --pdk-root "$pdk_root_container" "$CONFIG"
fi
