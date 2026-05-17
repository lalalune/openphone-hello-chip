# Interconnect contract

`rtl/interconnect/hello_axi_lite_interconnect.sv` is the first synthesizable interconnect scaffold for the Linux-capable SoC contract. It connects one CPU-side AXI-Lite manager port to DRAM and interrupt-controller target ports.

## Decode map

| Address range | Target | RTL target |
| ---: | --- | --- |
| `0x0C00_0000` - `0x0C00_0FFF` | Interrupt controller | `hello_interrupt_controller` |
| `0x8000_0000` - `0x8FFF_FFFF` | DRAM aperture | `hello_axi_lite_dram` model |
| Other | Decode error | AXI-Lite `DECERR`, read data `0xDEAD_BEEF` |

The existing hello-chip top remains a separate single-cycle MMIO validation design with its own map in `docs/arch/memory-map.md`. The AXI-Lite contract wrapper is `rtl/interconnect/hello_linux_soc_contract.sv` and is used by contract-level cocotb tests.

## Current limitations

The scaffold supports one outstanding read and one outstanding write transaction. The write address and write data channels may arrive independently, but the interconnect issues a target-side write only after both channels have been accepted. This intentionally avoids a full bus fabric while preserving the externally visible channel timing, response codes, and address decode rules needed by firmware and OS planning.

The contract wrapper uses CPU-wins arbitration when CPU and DMA requests target the same AXI-Lite path. DMA and CPU accesses must stay inside a bounded physical-address allowlist, and unsupported access paths fail closed.

No release, Android, AI-throughput, display-smoothness, or memory-bandwidth claim may rely on this scaffold until a real interconnect, memory controller, cache coherency, IOMMU, and QoS implementation has checked evidence.
