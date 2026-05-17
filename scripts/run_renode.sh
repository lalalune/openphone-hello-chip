#!/usr/bin/env sh
set -eu

if ! command -v renode >/dev/null 2>&1; then
    echo "Renode missing. qemu-virt platform stub is ready at sim/renode/openphone_hello.repl."
    exit 1
fi

echo "Launching Renode qemu-virt software reference target. This is not the hello-chip hardware ABI."
renode sim/renode/openphone_hello.resc
