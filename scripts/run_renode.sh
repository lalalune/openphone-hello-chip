#!/usr/bin/env sh
set -eu

if ! command -v renode >/dev/null 2>&1; then
    echo "Renode missing. Platform stub is ready at sim/renode/openphone_hello.repl."
    exit 1
fi

renode sim/renode/openphone_hello.resc
