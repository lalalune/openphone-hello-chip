import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


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


async def wait_write_response(dut, timeout_cycles=32):
    for _ in range(timeout_cycles):
        await Timer(1, units="ns")
        if int(dut.cpu_bvalid.value):
            resp = int(dut.cpu_bresp.value)
            await RisingEdge(dut.clk)
            return resp
        await RisingEdge(dut.clk)
    raise AssertionError("timeout waiting for AXI-Lite write response")


async def axil_write32_split(dut, addr, data, *, data_first=False, delay_cycles=3, strobe=0xF):
    dut.cpu_bready.value = 1
    dut.cpu_awaddr.value = addr
    dut.cpu_wdata.value = data
    dut.cpu_wstrb.value = strobe

    first_valid = dut.cpu_wvalid if data_first else dut.cpu_awvalid
    first_ready = dut.cpu_wready if data_first else dut.cpu_awready
    second_valid = dut.cpu_awvalid if data_first else dut.cpu_wvalid
    second_ready = dut.cpu_awready if data_first else dut.cpu_wready

    first_valid.value = 1
    while True:
        await Timer(1, units="ns")
        if int(first_ready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    first_valid.value = 0
    for _ in range(delay_cycles):
        await RisingEdge(dut.clk)

    second_valid.value = 1
    while True:
        await Timer(1, units="ns")
        if int(second_ready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    second_valid.value = 0
    return await wait_write_response(dut)


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
    assert resp == 3
    assert data == 0xDEAD_BEEF


@cocotb.test()
async def dram_aperture_outside_sram_model_returns_slverr(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0000, 0xA5A5_5A5A) == 0
    data, resp = await axil_read32(dut, 0x8000_0000)
    assert resp == 0
    assert data == 0xA5A5_5A5A

    # Inside the software-visible DRAM aperture, but outside the 4 KiB SRAM model.
    assert await axil_write32(dut, 0x8000_4000, 0x1122_3344) == 2
    data, resp = await axil_read32(dut, 0x8000_4000)
    assert resp == 2
    assert data == 0xDEAD_BEEF

    # Unaligned DRAM-local accesses are also target errors, not decode errors.
    assert await axil_write32(dut, 0x8000_0002, 0x5566_7788) == 2
    data, resp = await axil_read32(dut, 0x8000_0002)
    assert resp == 2
    assert data == 0xDEAD_BEEF


@cocotb.test()
async def axil_split_write_channels_complete_for_linux_master(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32_split(dut, 0x8000_0020, 0x1357_9BDF, delay_cycles=4) == 0
    data, resp = await axil_read32(dut, 0x8000_0020)
    assert resp == 0
    assert data == 0x1357_9BDF

    assert (
        await axil_write32_split(
            dut,
            0x0C00_0008,
            0b0101,
            data_first=True,
            delay_cycles=5,
        )
        == 0
    )
    data, resp = await axil_read32(dut, 0x0C00_0008)
    assert resp == 0
    assert data & 0b0101 == 0b0101

    assert (
        await axil_write32_split(
            dut,
            0x4000_0000,
            0xFFFF_0000,
            data_first=True,
            delay_cycles=2,
        )
        == 3
    )


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
async def dma_rejects_unaligned_and_reports_memory_errors(dut):
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


@cocotb.test()
async def dma_non_dram_targets_fault_without_mmio_side_effects(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x0C00_0008, 0x0) == 0
    assert await axil_write32(dut, 0x8000_0040, 0xCAFE_BABE) == 0

    assert await axil_write32(dut, 0x1001_0000, 0x8000_0040) == 0
    assert await axil_write32(dut, 0x1001_0004, 0x0C00_0008) == 0
    assert await axil_write32(dut, 0x1001_0008, 4) == 0
    assert await axil_write32(dut, 0x1001_000C, 1) == 0
    _, status = await wait_dma_done(dut)
    assert status & 0x6 == 0x6

    data, resp = await axil_read32(dut, 0x0C00_0008)
    assert resp == 0
    assert data == 0

    data, resp = await axil_read32(dut, 0x1001_0038)
    assert resp == 0
    assert data == 1

    assert await axil_write32(dut, 0x1001_000C, 2) == 0
    assert await axil_write32(dut, 0x1001_0000, 0x0C00_0000) == 0
    assert await axil_write32(dut, 0x1001_0004, 0x8000_0080) == 0
    assert await axil_write32(dut, 0x1001_0008, 4) == 0
    assert await axil_write32(dut, 0x1001_000C, 1) == 0
    _, status = await wait_dma_done(dut)
    assert status & 0x6 == 0x6

    data, resp = await axil_read32(dut, 0x8000_0080)
    assert resp == 0
    assert data != 0x1C00_0001
