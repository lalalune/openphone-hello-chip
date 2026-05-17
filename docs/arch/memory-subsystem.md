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

Real DRAM, PHY timing, refresh, training, ECC, cache coherency, IOMMU/SMMU, and QoS are not implemented by the current scaffold. This is a real memory controller boundary only: the checked-in model is SRAM-backed, has no cache coherency, no IOMMU, and no QoS.

Any software or product claim that depends on a real memory hierarchy must fail closed until controller, PHY, coherency, IOMMU, and QoS evidence is checked in.
