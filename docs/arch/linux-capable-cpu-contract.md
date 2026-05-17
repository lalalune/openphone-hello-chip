# Linux-Capable CPU Contract

`rtl/cpu/hello_cpu_subsystem_stub.sv` is a tiny executable contract model. It
is useful for fetch/execute, bus, and negative trap tests, but it is not a
Linux-capable application processor.

Required closure before any CPU/AP claim:

- A production-named CPU/AP top wrapper, with any legacy `stub` wrapper kept
  below the release claim boundary.
- RV64GC or explicitly justified RV64 Linux-capable ISA support.
- MMU, privilege, CSR, timer, interrupt, cache, and memory-ordering evidence.
- OpenSBI boot log, Linux early-console boot log, and trap/timer IRQ transcript
  under `build/evidence/cpu_ap/`.
- Linux early console must show firmware-to-kernel handoff details, including
  `mcause`, `mepc`, `mtimecmp`, and external interrupt claim/complete behavior.
- Fail-closed gates that separate scaffold presence from executable hardware
  evidence: `make cpu-ap-scaffold-check` may pass, while
  `make cpu-ap-evidence-check` must block until real evidence exists.
