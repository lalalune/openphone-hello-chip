#!/usr/bin/env sh
set -eu

IMAGE="${OPENLANE_IMAGE:-ghcr.io/efabless/openlane2:2.4.0.dev1}"
docker pull "$IMAGE"
docker image inspect "$IMAGE" >/dev/null
echo "OpenLane image installed: $IMAGE"
