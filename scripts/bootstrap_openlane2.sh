#!/usr/bin/env sh
set -eu

mkdir -p external
if [ ! -d external/openlane2 ]; then
    git clone https://github.com/efabless/openlane2.git external/openlane2
fi

cd external/openlane2
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install .

echo "OpenLane2 Python entry point installed in external/openlane2/.venv."
echo "A PDK is still required before running pd/openlane/config.json."
