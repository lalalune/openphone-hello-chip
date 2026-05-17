#!/usr/bin/env sh
set -eu

MANIFEST="${CHIPYARD_MANIFEST:-generators/chipyard/openphone-rocket-manifest.json}"

CHIPYARD_REPO="${CHIPYARD_REPO:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["repo"])' "$MANIFEST")}"
CHIPYARD_TAG="${CHIPYARD_TAG:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["tag"])' "$MANIFEST")}"
CHIPYARD_SHA="${CHIPYARD_SHA:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["commit"])' "$MANIFEST")}"

if [ -z "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: CHIPYARD_SHA must be set." >&2
    exit 2
fi

mkdir -p external
if [ ! -d external/chipyard ]; then
    git clone "$CHIPYARD_REPO" external/chipyard
fi

cd external/chipyard
git fetch --tags origin
tag_sha="$(git rev-list -n 1 "$CHIPYARD_TAG")"
if [ "$tag_sha" != "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: tag $CHIPYARD_TAG resolves to $tag_sha, expected $CHIPYARD_SHA" >&2
    exit 1
fi
git checkout --detach "$CHIPYARD_SHA"
git submodule update --init --recursive

resolved="$(git rev-parse HEAD)"
if [ "$resolved" != "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: resolved HEAD ($resolved) != pinned SHA ($CHIPYARD_SHA)" >&2
    exit 1
fi

echo "Chipyard $CHIPYARD_TAG checked out under external/chipyard at $CHIPYARD_SHA."
echo "Follow Chipyard's setup docs for the selected host/container before building generators."
