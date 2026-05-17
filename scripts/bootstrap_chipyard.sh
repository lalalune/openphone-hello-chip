#!/usr/bin/env sh
set -eu

REPO_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR"

MANIFEST="${CHIPYARD_MANIFEST:-generators/chipyard/openphone-rocket-manifest.json}"
CHECKOUT="${CHIPYARD_CHECKOUT:-external/chipyard}"

CHIPYARD_REPO="${CHIPYARD_REPO:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["repo"])' "$MANIFEST")}"
CHIPYARD_TAG="${CHIPYARD_TAG:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["tag"])' "$MANIFEST")}"
CHIPYARD_SHA="${CHIPYARD_SHA:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["chipyard"]["commit"])' "$MANIFEST")}"

if [ -z "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: CHIPYARD_SHA must be set." >&2
    exit 2
fi

mkdir -p external
if [ ! -d "$CHECKOUT" ]; then
    git clone "$CHIPYARD_REPO" "$CHECKOUT"
fi

cd "$CHECKOUT"
git fetch --tags origin
tag_sha="$(git rev-list -n 1 "$CHIPYARD_TAG")"
if [ "$tag_sha" != "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: tag $CHIPYARD_TAG resolves to $tag_sha, expected $CHIPYARD_SHA" >&2
    exit 1
fi
git checkout --detach "$CHIPYARD_SHA"
git submodule update --init --recursive generators/rocket-chip
git submodule update --init \
    tools/cde \
    tools/firrtl2 \
    tools/install-circt \
    tools/rocket-dsp-utils \
    generators/bar-fetchers \
    generators/rocc-acc-utils \
    sims/verilator \
    software/firemarshal

resolved="$(git rev-parse HEAD)"
if [ "$resolved" != "$CHIPYARD_SHA" ]; then
    echo "bootstrap_chipyard: resolved HEAD ($resolved) != pinned SHA ($CHIPYARD_SHA)" >&2
    exit 1
fi

cd "$REPO_DIR"
python3 - "$MANIFEST" "$CHECKOUT" <<'PY'
import json
import shutil
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checkout = Path(sys.argv[2])
for entry in manifest["selected_path"].get("config_sources", []):
    source = Path(entry["source"])
    destination = checkout / entry["checkout_destination"]
    if not source.is_file():
        raise SystemExit(f"bootstrap_chipyard: missing config source overlay: {source}")
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise SystemExit(
            "bootstrap_chipyard: refusing to overwrite different checkout overlay "
            f"{destination}; inspect it or remove it before rerunning"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"Installed Chipyard config overlay: {source} -> {destination}")
PY

python3 scripts/check_chipyard_import_preflight.py --checkout "$CHECKOUT" --require-checkout

echo "Chipyard $CHIPYARD_TAG checked out under $CHECKOUT at $CHIPYARD_SHA."
echo "Follow Chipyard's setup docs for the selected host/container before building generators."
