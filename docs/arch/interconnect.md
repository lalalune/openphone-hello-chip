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

## DMA containment boundary

The current DMA path is not an IOMMU. It is a bounded scaffold path: CPU-side software programs the DMA registers through the `0x1001_0000` MMIO window, and DMA master reads/writes are routed only to the SRAM-backed DRAM model. DMA attempts to use interrupt-controller, peripheral, or other MMIO addresses are expected to return DRAM-model `SLVERR` after address translation into the DRAM target and must not mutate those MMIO registers. `verify/cocotb/test_cpu_mem_intc_contract.py` covers this negative path.

This proves local address containment for the scaffold only. Coherent DMA, page-table translation, fault reporting to a kernel driver, and production IOMMU/SMMU behavior remain blocked.
