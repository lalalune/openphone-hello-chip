import json
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

REPO_ROOT = Path(__file__).resolve().parents[2]


async def reset(dut):
    dut.rst_n.value = 0
    dut.cpu_awvalid.value = 0
    dut.cpu_awaddr.value = 0
    dut.cpu_wvalid.value = 0
    dut.cpu_wdata.value = 0
    dut.cpu_wstrb.value = 0
    dut.cpu_bready.value = 1
    dut.cpu_arvalid.value = 0
    dut.cpu_araddr.value = 0
    dut.cpu_rready.value = 1
    dut.irq_sources.value = 0
    await Timer(1, units="ns")
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def axil_write32(dut, addr, data, strobe=0xF):
    dut.cpu_awaddr.value = addr
    dut.cpu_wdata.value = data
    dut.cpu_wstrb.value = strobe
    dut.cpu_awvalid.value = 1
    dut.cpu_wvalid.value = 1
    dut.cpu_bready.value = 1

    while True:
        await Timer(1, units="ns")
        if int(dut.cpu_awready.value) and int(dut.cpu_wready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    dut.cpu_awvalid.value = 0
    dut.cpu_wvalid.value = 0

    while True:
        await Timer(1, units="ns")
        if int(dut.cpu_bvalid.value):
            resp = int(dut.cpu_bresp.value)
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    return resp


async def axil_split_write32(dut, addr, data, strobe=0xF, data_first=False, gap_cycles=3):
    dut.cpu_bready.value = 1

    if data_first:
        dut.cpu_wdata.value = data
        dut.cpu_wstrb.value = strobe
        dut.cpu_wvalid.value = 1
        while True:
            await Timer(1, units="ns")
            if int(dut.cpu_wready.value):
                break
            await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.cpu_wvalid.value = 0

        for _ in range(gap_cycles):
            await RisingEdge(dut.clk)

        dut.cpu_awaddr.value = addr
        dut.cpu_awvalid.value = 1
        while True:
            await Timer(1, units="ns")
            if int(dut.cpu_awready.value):
                break
            await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.cpu_awvalid.value = 0
    else:
        dut.cpu_awaddr.value = addr
        dut.cpu_awvalid.value = 1
        while True:
            await Timer(1, units="ns")
            if int(dut.cpu_awready.value):
                break
            await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.cpu_awvalid.value = 0

        for _ in range(gap_cycles):
            await RisingEdge(dut.clk)

        dut.cpu_wdata.value = data
        dut.cpu_wstrb.value = strobe
        dut.cpu_wvalid.value = 1
        while True:
            await Timer(1, units="ns")
            if int(dut.cpu_wready.value):
                break
            await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.cpu_wvalid.value = 0

    while True:
        await Timer(1, units="ns")
        if int(dut.cpu_bvalid.value):
            resp = int(dut.cpu_bresp.value)
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    return resp


async def axil_read32(dut, addr):
    dut.cpu_araddr.value = addr
    dut.cpu_arvalid.value = 1
    dut.cpu_rready.value = 1

    while True:
        await Timer(1, units="ns")
        if int(dut.cpu_arready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    dut.cpu_arvalid.value = 0

    while True:
        await Timer(1, units="ns")
        if int(dut.cpu_rvalid.value):
            data = int(dut.cpu_rdata.value)
            resp = int(dut.cpu_rresp.value)
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    return data, resp


def write_coverage_artifact(extra):
    coverage = {
        "schema": "hello-chip.cpu_mem_intc_cocotb_coverage.v1",
        "source": "verify/cocotb/test_cpu_mem_intc_contract.py",
        "covered_contracts": sorted(extra),
        "boundary": "Directed AXI-Lite memory and interrupt-controller contract checks around the tiny CPU harness only; no application-class CPU, MMU, cache, Linux, or Android boot coverage.",
    }
    out = REPO_ROOT / "build/reports/cpu_mem_intc_cocotb_coverage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@cocotb.test()
async def axi_lite_split_write_channels_are_captured_independently(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_split_write32(dut, 0x8000_0020, 0xCAFE_BABE) == 0
    data, resp = await axil_read32(dut, 0x8000_0020)
    assert resp == 0
    assert data == 0xCAFE_BABE

    assert await axil_split_write32(dut, 0x8000_0024, 0x1122_3344, data_first=True) == 0
    data, resp = await axil_read32(dut, 0x8000_0024)
    assert resp == 0
    assert data == 0x1122_3344


@cocotb.test()
async def dram_axil_boundary_round_trips(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0010, 0x1122_3344) == 0
    data, resp = await axil_read32(dut, 0x8000_0010)
    assert resp == 0
    assert data == 0x1122_3344

    assert await axil_write32(dut, 0x8000_0010, 0xAA00_0000, strobe=0x8) == 0
    data, resp = await axil_read32(dut, 0x8000_0010)
    assert resp == 0
    assert data == 0xAA22_3344

    data, resp = await axil_read32(dut, 0x4000_0000)
    assert resp == 2
    assert data == 0xDEAD_BEEF


@cocotb.test()
async def dram_aperture_outside_sram_model_returns_slverr(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0FFC, 0x55AA_1234) == 0
    data, resp = await axil_read32(dut, 0x8000_0FFC)
    assert resp == 0
    assert data == 0x55AA_1234

    assert await axil_write32(dut, 0x8000_1000, 0xCAFE_BABE) == 2
    data, resp = await axil_read32(dut, 0x8000_1000)
    assert resp == 2
    assert data == 0xDEAD_BEEF


@cocotb.test()
async def interrupt_controller_claim_complete_contract(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    data, resp = await axil_read32(dut, 0x0C00_0000)
    assert resp == 0
    assert data == 0x1C00_0001

    assert await axil_write32(dut, 0x0C00_0008, 0b1010) == 0
    dut.irq_sources.value = 0b0010
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    data, resp = await axil_read32(dut, 0x0C00_0004)
    assert resp == 0
    assert data & 0b0010
    assert int(dut.cpu_external_irq.value) == 1

    data, resp = await axil_read32(dut, 0x0C00_000C)
    assert resp == 0
    assert data == 2

    dut.irq_sources.value = 0
    assert await axil_write32(dut, 0x0C00_000C, 2) == 0
    await RisingEdge(dut.clk)
    data, resp = await axil_read32(dut, 0x0C00_0004)
    assert resp == 0
    assert data == 0
    assert int(dut.cpu_external_irq.value) == 0


@cocotb.test()
async def interrupt_controller_masks_disabled_sources_but_keeps_pending(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    dut.irq_sources.value = 0b0101
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    data, resp = await axil_read32(dut, 0x0C00_0004)
    assert resp == 0
    assert data & 0b0101 == 0b0101
    assert int(dut.cpu_external_irq.value) == 0

    assert await axil_write32(dut, 0x0C00_0008, 0b0001) == 0
    assert int(dut.cpu_external_irq.value) == 1
    data, resp = await axil_read32(dut, 0x0C00_000C)
    assert resp == 0
    assert data == 1

    dut.irq_sources.value = 0
    assert await axil_write32(dut, 0x0C00_000C, 1) == 0
    await RisingEdge(dut.clk)
    assert int(dut.cpu_external_irq.value) == 0
    data, resp = await axil_read32(dut, 0x0C00_0004)
    assert resp == 0
    assert data & 0b0100 == 0b0100

    assert await axil_write32(dut, 0x0C00_0008, 0b0100) == 0
    data, resp = await axil_read32(dut, 0x0C00_000C)
    assert resp == 0
    assert data == 3

    write_coverage_artifact(
        {"split_axil_write", "dram_strobes", "interrupt_mask_pending_claim_complete"}
    )


async def wait_dma_done(dut, timeout_cycles=100):
    for cycle in range(timeout_cycles):
        data, resp = await axil_read32(dut, 0x1001_000C)
        assert resp == 0
        if data & 0x2:
            return cycle + 1, data
    raise AssertionError("DMA did not complete")


@cocotb.test()
async def dma_bus_master_copies_dram_and_reports_counters(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0040, 0x1122_3344) == 0
    assert await axil_write32(dut, 0x8000_0044, 0x5566_7788) == 0

    assert await axil_write32(dut, 0x1001_0000, 0x8000_0040) == 0
    assert await axil_write32(dut, 0x1001_0004, 0x8000_0080) == 0
    assert await axil_write32(dut, 0x1001_0008, 8) == 0
    assert await axil_write32(dut, 0x1001_000C, 1) == 0

    cycles, status = await wait_dma_done(dut)
    assert status & 0x1 == 0
    assert status & 0x4 == 0
    assert 4 <= cycles <= 40

    data, resp = await axil_read32(dut, 0x8000_0080)
    assert resp == 0
    assert data == 0x1122_3344
    data, resp = await axil_read32(dut, 0x8000_0084)
    assert resp == 0
    assert data == 0x5566_7788

    data, resp = await axil_read32(dut, 0x1001_0014)
    assert resp == 0
    assert data == 8
    data, resp = await axil_read32(dut, 0x1001_0018)
    assert resp == 0
    assert data == 2
    data, resp = await axil_read32(dut, 0x1001_0030)
    assert resp == 0
    assert data == 2
    data, resp = await axil_read32(dut, 0x1001_0034)
    assert resp == 0
    assert data == 2


@cocotb.test()
async def dma_non_dram_targets_fault_without_mmio_side_effects(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x1001_0000, 0x8000_0041) == 0
    assert await axil_write32(dut, 0x1001_0004, 0x8000_0080) == 0
    assert await axil_write32(dut, 0x1001_0008, 4) == 0
    assert await axil_write32(dut, 0x1001_000C, 1) == 0
    data, resp = await axil_read32(dut, 0x1001_000C)
    assert resp == 0
    assert data & 0x6 == 0x6

    assert await axil_write32(dut, 0x1001_000C, 2) == 0
    assert await axil_write32(dut, 0x1001_0000, 0x9000_0000) == 0
    assert await axil_write32(dut, 0x1001_0004, 0x8000_0080) == 0
    assert await axil_write32(dut, 0x1001_0008, 4) == 0
    assert await axil_write32(dut, 0x1001_000C, 1) == 0
    _, status = await wait_dma_done(dut)
    assert status & 0x6 == 0x6
    data, resp = await axil_read32(dut, 0x1001_0038)
    assert resp == 0
    assert data == 1
    mask, resp = await axil_read32(dut, 0x0C00_0008)
    assert resp == 0
    assert mask == 0
