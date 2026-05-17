#!/usr/bin/env sh
set -eu

# Chipyard pinned reference for reproducible RTL generator builds.
#
# TODO(toolchain-ci): replace CHIPYARD_SHA_PLACEHOLDER with the reviewed
# upstream commit selected per docs/toolchain/reproducibility.md. The repo
# previously cloned chipyard's default branch which made the toolchain
# non-reproducible. Until a SHA is selected we hard-fail unless the operator
# opts in by exporting CHIPYARD_SHA explicitly (e.g. for evaluation builds).
#
# To discover candidate SHAs:
#   git ls-remote https://github.com/ucb-bar/chipyard.git refs/tags/'*'
# Pick a tagged release, paste its commit hash here, and remove the TODO.

CHIPYARD_REPO="${CHIPYARD_REPO:-https://github.com/ucb-bar/chipyard.git}"
CHIPYARD_SHA="${CHIPYARD_SHA:-CHIPYARD_SHA_PLACEHOLDER}"

if [ "$CHIPYARD_SHA" = "CHIPYARD_SHA_PLACEHOLDER" ]; then
    cat >&2 <<'EOF'
bootstrap_chipyard: CHIPYARD_SHA is not pinned.
  Export CHIPYARD_SHA=<commit> to override for evaluation builds, or replace
  the placeholder in scripts/bootstrap_chipyard.sh with a reviewed SHA.
  See docs/toolchain/reproducibility.md.
EOF
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
