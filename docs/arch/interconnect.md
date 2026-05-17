# Interconnect contract

`rtl/interconnect/hello_axi_lite_interconnect.sv` is the first synthesizable interconnect scaffold for the Linux-capable SoC contract. It connects one CPU-side AXI-Lite manager port to DRAM, interrupt-controller, and DMA-control target ports. `rtl/interconnect/hello_linux_soc_contract.sv` also arbitrates the prototype DMA AXI-Lite master onto the same DRAM model used by CPU-side traffic.

## Decode map

| Address range | Target | RTL target |
| ---: | --- | --- |
| `0x0C00_0000` - `0x0C00_0FFF` | Interrupt controller | `hello_interrupt_controller` |
| `0x1001_0000` - `0x1001_0FFF` | DMA control | `hello_dma` MMIO target wrapper |
| `0x8000_0000` - `0x8FFF_FFFF` | DRAM aperture | `hello_axi_lite_dram` model |
| Other | Decode error | AXI-Lite `DECERR`, read data `0xDEAD_BEEF` |

The existing hello-chip top remains a separate single-cycle MMIO validation design with its own map in `docs/arch/memory-map.md`. The AXI-Lite contract wrapper is `rtl/interconnect/hello_linux_soc_contract.sv` and is used by contract-level cocotb tests.

## Current limitations

The scaffold supports one outstanding read and one outstanding write transaction. The write address and write data channels may arrive independently, but the interconnect issues a target-side write only after both channels have been accepted. This intentionally avoids a full bus fabric while preserving the externally visible channel timing, response codes, and address decode rules needed by firmware and OS planning.

The DMA/CPU merge point in `rtl/interconnect/hello_linux_soc_contract.sv` is a fixed CPU-priority mux into the SRAM-backed DRAM model. It is not a cache-coherent fabric, not a QoS arbiter, and not evidence for bandwidth fairness, latency bounds, burst behavior, ordering between independent masters, or starvation freedom. Any future production fabric must add explicit arbitration policy, outstanding transaction limits, response-ordering rules, performance counters, and contended latency/bandwidth evidence before CPU, DMA, display, NPU, camera/ISP, or GPU/2D traffic claims can be made.

## DMA containment boundary

The current DMA path is not an IOMMU. It is a bounded scaffold path: CPU-side software programs the DMA registers through the `0x1001_0000` MMIO window, and DMA master reads/writes are routed only to the SRAM-backed DRAM model. DMA attempts to use interrupt-controller, peripheral, or other MMIO addresses are expected to return DRAM-model `SLVERR` after address translation into the DRAM target and must not mutate those MMIO registers. `verify/cocotb/test_cpu_mem_intc_contract.py` covers this negative path.

This proves local address containment for the scaffold only. Coherent DMA, page-table translation, fault reporting to a kernel driver, and production IOMMU/SMMU behavior remain blocked.

## Production fabric gates

A Linux/Android-capable interconnect must make the following contracts executable before it can replace the scaffold:

| Gate | Required production contract |
| --- | --- |
| Coherency | Declare coherent DMA support or a non-coherent ownership/cache-maintenance ABI for every DMA-capable client. |
| IOMMU/SMMU | Place every bus master behind a translated or explicitly allowlisted domain; unauthorized transactions must fault without MMIO side effects. |
| Fault reporting | Surface page fault reporting to software with master ID, address, access type, permission/syndrome bits, and recovery behavior. |
| QoS | Specify arbitration, priority, starvation bounds, counters, and bandwidth/latency budgets for CPU, DMA, NPU, display, camera/ISP, and GPU/2D traffic. |
| CLINT/PLIC access map | Reserve CLINT/ACLINT and PLIC/IMSIC windows from DMA, document CPU privilege access, and prove DMA cannot mutate timer or interrupt-controller state. |
| DRAM/LPDDR path | Attach a real DRAM controller/PHY or integrated IP boundary with measured LPDDR bandwidth/latency evidence; the current SRAM model cannot satisfy this gate. |

Phone-class 2028 memory claims remain blocked until `docs/evidence/memory/uma-dram-evidence-gate.yaml` is intentionally replaced or satisfied with real DRAM, cache hierarchy, UMA/coherency, IOMMU/SMMU, and contended bandwidth and latency artifacts.
