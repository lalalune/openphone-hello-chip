import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def reset(dut):
    dut.rst_n.value = 0
    dut.mmio_valid.value = 0
    dut.mmio_write.value = 0
    dut.mmio_addr.value = 0
    dut.mmio_wdata.value = 0
    await Timer(1, units="ns")
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def write32(dut, addr, data):
    dut.mmio_addr.value = addr
    dut.mmio_wdata.value = data
    dut.mmio_write.value = 1
    dut.mmio_valid.value = 1
    await RisingEdge(dut.clk)
    dut.mmio_valid.value = 0
    dut.mmio_write.value = 0
    await RisingEdge(dut.clk)


async def read32(dut, addr):
    dut.mmio_addr.value = addr
    dut.mmio_write.value = 0
    dut.mmio_valid.value = 1
    await Timer(1, units="ns")
    value = int(dut.mmio_rdata.value)
    await RisingEdge(dut.clk)
    dut.mmio_valid.value = 0
    await RisingEdge(dut.clk)
    return value


@cocotb.test()
async def bootrom_and_gpio_contract(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await read32(dut, 0x0000_0000) == 0x4F50_534F
    assert await read32(dut, 0x0000_0004) == 0x4348_4950

    await write32(dut, 0x1000_0008, 0xA5)
    assert await read32(dut, 0x1000_0008) == 0xA5
    assert int(dut.gpio_out.value) == 0xA5


@cocotb.test()
async def timer_dma_npu_display_interrupts(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write32(dut, 0x1000_0010, 8)
    for _ in range(10):
        await RisingEdge(dut.clk)
    assert int(dut.irq_timer.value) == 1

    await write32(dut, 0x1001_0000, 0x1000)
    await write32(dut, 0x1001_0004, 0x2000)
    await write32(dut, 0x1001_0008, 64)
    await write32(dut, 0x1001_000C, 1)
    for _ in range(6):
        await RisingEdge(dut.clk)
    assert int(dut.irq_dma.value) == 1

    await write32(dut, 0x1002_0000, 17)
    await write32(dut, 0x1002_0004, 25)
    await write32(dut, 0x1002_000C, 1)
    for _ in range(4):
        await RisingEdge(dut.clk)
    assert await read32(dut, 0x1002_0008) == 42
    assert int(dut.irq_npu.value) == 1

    await write32(dut, 0x1003_0000, 0x8000_0000)
    await write32(dut, 0x1003_0004, (480 << 16) | 640)
    await write32(dut, 0x1003_000C, 1)
    assert await read32(dut, 0x1003_0000) == 0x8000_0000


@cocotb.test()
async def reset_unmapped_and_clear_edges(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await read32(dut, 0x1000_0004) == 0
    assert await read32(dut, 0x1000_0008) == 0
    assert await read32(dut, 0x2000_0000) == 0xDEAD_BEEF

    await write32(dut, 0x1002_0000, 0xFFFF_FFFF)
    await write32(dut, 0x1002_0004, 1)
    await write32(dut, 0x1002_000C, 1)
    for _ in range(4):
        await RisingEdge(dut.clk)
    assert await read32(dut, 0x1002_0008) == 0
    assert int(dut.irq_npu.value) == 1
    await write32(dut, 0x1002_000C, 2)
    assert int(dut.irq_npu.value) == 0

    await write32(dut, 0x1001_0008, 0)
    await write32(dut, 0x1001_000C, 1)
    for _ in range(6):
        await RisingEdge(dut.clk)
    assert int(dut.irq_dma.value) == 1
    await write32(dut, 0x1001_000C, 2)
    assert int(dut.irq_dma.value) == 0


@cocotb.test()
async def display_enable_gates_vsync(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    for _ in range(260):
        await RisingEdge(dut.clk)
    assert int(dut.irq_vsync.value) == 0

    await write32(dut, 0x1003_000C, 1)
    seen = False
    for _ in range(260):
        await RisingEdge(dut.clk)
        seen = seen or int(dut.irq_vsync.value) == 1
    assert seen
