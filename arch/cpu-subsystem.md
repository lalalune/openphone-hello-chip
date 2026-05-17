# CPU subsystem contract

The repository carries a synthesizable CPU boundary without claiming to implement a CPU core. `rtl/cpu/hello_cpu_subsystem_stub.sv` is a quiescent placeholder for the future application CPU subsystem.

## Boundary

The CPU subsystem boundary is a single 32-bit AXI-Lite manager port:

```text
AW: awvalid, awready, awaddr[31:0]
W:  wvalid, wready, wdata[31:0], wstrb[3:0]
B:  bvalid, bready, bresp[1:0]
AR: arvalid, arready, araddr[31:0]
R:  rvalid, rready, rdata[31:0], rresp[1:0]
```

The stub drives no transactions, always accepts responses, exports `reset_pc` and `hart_id`, and reports combined interrupt pending state. This is enough for synthesis, integration checks, and top-level wiring while a real RV64GC application CPU remains out of scope for the hello-chip milestone.

## Linux-capable target

| Contract item | Target |
| --- | --- |
| ISA | RV64GC application hart, plus platform-defined management hart if needed |
| Reset | `reset_pc` points at boot ROM or firmware entry |
| Interrupts | Timer, software, and external interrupt inputs compatible with OpenSBI/Linux expectations |
| Memory access | AXI/TileLink-class manager path, represented here by the 32-bit AXI-Lite scaffold |
| Coherency | Not modeled in the current scaffold |
| MMU/cache | Not modeled in the current scaffold |

The scaffold is intentionally not instruction-set compatible and must not be treated as a bootable CPU model.
