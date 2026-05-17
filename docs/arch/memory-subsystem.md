# Memory subsystem contract

`rtl/memory/hello_axi_lite_dram.sv` provides the current synthesizable DRAM boundary model. It is a small AXI-Lite SRAM-backed stand-in for an external DRAM controller and PHY.

## AXI-Lite behavior

| Property | Current scaffold |
| --- | --- |
| Data width | 32 bits |
| Address width | 32 bits at the SoC boundary |
| Write strobes | Byte strobes honored |
| Outstanding requests | One write response and one read response at a time |
| Response codes | `OKAY` for implemented aligned accesses, `SLVERR` for out-of-range or unaligned DRAM-local accesses |
| Reset contents | Unspecified |

The model accepts independently arriving write address and write data channels. It performs the write only after both channels have been captured.

## DRAM target

The long-term Linux-capable target reserves `0x8000_0000` and above for system DRAM. The RTL model only implements a small local window under that aperture for tests and synthesis. A real integration will replace the model with a memory controller boundary while preserving the software-visible base address.

## Claim boundary

The current memory path is scaffold evidence only. It is SRAM-backed storage with AXI-Lite response behavior, not real DRAM capacity or timing evidence. It does not implement a DRAM controller, LPDDR/DDR PHY, training, refresh, ECC, cache hierarchy, UMA coherency protocol, coherent DMA, IOMMU/SMMU translation, page-fault reporting, memory QoS, bandwidth counters, or display/NPU contention guarantees.

`docs/evidence/memory/uma-dram-evidence-gate.yaml` is the local evidence gate for this boundary. Passing that gate means the repository distinguishes the SRAM-backed DMA containment scaffold from real DRAM/UMA/coherency/IOMMU work; it must not be used as release evidence for Android shared buffers, AI throughput, display smoothness, memory bandwidth, or tapeout readiness.
