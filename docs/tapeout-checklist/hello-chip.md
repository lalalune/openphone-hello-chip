# Hello chip tapeout-readiness checklist

The hello chip is ready as a pipeline milestone when:

- RTL syntax/elaboration passes.
- cocotb register tests pass.
- Verilator smoke test passes.
- DMA and NPU formal checks pass.
- Yosys synthesis emits a netlist and area report.
- OpenLane or OpenROAD either completes or has a documented tool/PDK blocker.
- Memory map and interrupt map match the tests.
- All generated reports are stored under `build/` or `pd/reports/`.
