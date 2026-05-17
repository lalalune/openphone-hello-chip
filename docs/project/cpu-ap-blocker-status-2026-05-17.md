# CPU/AP Blocker Status

The current checked-in CPU path is a tiny executable scaffold for contract
tests. It is not a Linux-capable application processor and must not be used as
phone CPU evidence.

## Current Gate

- The platform contract remains `has_cpu=false` until a production CPU is
  integrated at the package top.
- No generated Chipyard/Rocket RTL is checked in for the product CPU/AP path.
- OpenSBI plus Linux early console evidence is missing.

## Required Evidence

Before any Linux-capable CPU claim is unblocked, the repo needs checked
transcripts for OpenSBI, Linux early console, trap and interrupt behavior,
`mcause`, `mepc`, `mtimecmp`, external interrupt claim/complete, and
firmware-to-kernel handoff.
