#!/usr/bin/env sh
set -eu

mkdir -p external
if [ ! -d external/chipyard ]; then
    git clone https://github.com/ucb-bar/chipyard.git external/chipyard
fi

cd external/chipyard
git submodule update --init --recursive

echo "Chipyard checked out under external/chipyard."
echo "Follow Chipyard's setup docs for the selected host/container before building generators."
