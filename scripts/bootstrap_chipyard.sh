#!/usr/bin/env sh
set -eu

# Chipyard pinned reference for reproducible RTL generator builds.
#
# Pinned to Chipyard release 1.12.0 (see docs/rtl/cpu-config-selection.md and
# docs/toolchain/reproducibility.md). Verify by re-running:
#   git ls-remote https://github.com/ucb-bar/chipyard refs/tags/1.12.0

CHIPYARD_REPO="${CHIPYARD_REPO:-https://github.com/ucb-bar/chipyard.git}"
CHIPYARD_SHA="${CHIPYARD_SHA:-404c8d361de98a98967f5d7a9bf51cbe8434d4c9}"

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
git checkout --detach "$CHIPYARD_SHA"
git submodule update --init --recursive

resolved="$(git rev-parse HEAD)"
if [ "$resolved" != "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: resolved HEAD ($resolved) != pinned SHA ($CHIPYARD_SHA)" >&2
    exit 1
fi

echo "Chipyard checked out under external/chipyard at $CHIPYARD_SHA."
echo "Follow Chipyard's setup docs for the selected host/container before building generators."
