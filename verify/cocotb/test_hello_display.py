import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def reset(dut):
    dut.rst_n.value = 0
    dut.valid.value = 0
    dut.write.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    await Timer(1, units="ns")
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def write_reg(dut, addr, data):
    dut.addr.value = addr
    dut.wdata.value = data
    dut.write.value = 1
    dut.valid.value = 1
    await RisingEdge(dut.clk)
    dut.valid.value = 0
    dut.write.value = 0
    await Timer(1, units="ns")


async def read_reg(dut, addr):
    dut.addr.value = addr
    dut.write.value = 0
    dut.valid.value = 1
    await Timer(1, units="ns")
    value = int(dut.rdata.value)
    await RisingEdge(dut.clk)
    dut.valid.value = 0
    await Timer(1, units="ns")
    return value


async def advance(dut, cycles):
    for _ in range(cycles):
        await RisingEdge(dut.clk)
    await Timer(1, units="ns")


@cocotb.test()
async def display_register_defaults_and_disable_gate_scanout(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await read_reg(dut, 0) == 0
    assert await read_reg(dut, 1) == (480 << 16) | 640
    assert await read_reg(dut, 2) == 0x3432_5258
    assert await read_reg(dut, 3) == 0
    assert await read_reg(dut, 4) == 0

    await advance(dut, 32)
    assert int(dut.scan_active.value) == 0
    assert int(dut.scan_hsync.value) == 0
    assert int(dut.scan_vsync.value) == 0
    assert int(dut.irq_vsync.value) == 0
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 0
    assert int(dut.scan_fb_addr.value) == 0


@cocotb.test()
async def display_clamps_mode_and_rejects_unsupported_format(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 1, 0)
    assert await read_reg(dut, 1) == (1 << 16) | 1

    await write_reg(dut, 2, 0x3432_4247)  # XB24/GB24-like value is not implemented.
    assert await read_reg(dut, 2) == 0x3432_5258

    await write_reg(dut, 2, 0x3432_5258)
    assert await read_reg(dut, 2) == 0x3432_5258


@cocotb.test()
async def display_generates_active_pixels_and_hsync(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0, 0x8000_0000)
    await write_reg(dut, 1, (3 << 16) | 4)
    await write_reg(dut, 3, 1)

    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 0
    assert int(dut.scan_fb_addr.value) == 0x8000_0000
    assert int(dut.scan_rgb.value) == 0

    await advance(dut, 1)
    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_x.value) == 1
    assert int(dut.scan_fb_addr.value) == 0x8000_0004
    assert int(dut.scan_rgb.value) == 0x010001

    await advance(dut, 3)
    assert int(dut.scan_active.value) == 0
    assert int(dut.scan_x.value) == 4
    assert int(dut.scan_fb_addr.value) == 0

    await advance(dut, 16)
    assert int(dut.scan_x.value) == 20
    assert int(dut.scan_hsync.value) == 1
    assert int(dut.scan_vsync.value) == 0

    await advance(dut, 96)
    assert int(dut.scan_x.value) == 116
    assert int(dut.scan_hsync.value) == 0


@cocotb.test()
async def display_generates_vsync_pulse_and_wraps_frame(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 1, (3 << 16) | 4)
    await write_reg(dut, 3, 1)

    total_h = 4 + 16 + 96 + 48
    total_v = 3 + 10 + 2 + 33

    await advance(dut, total_h * (3 + 10))
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 13
    assert int(dut.scan_active.value) == 0
    assert int(dut.scan_vsync.value) == 1
    assert int(dut.irq_vsync.value) == 1
    assert await read_reg(dut, 4) == 1

    await advance(dut, 1)
    assert int(dut.irq_vsync.value) == 0

    await advance(dut, total_h * total_v - (total_h * (3 + 10)) - 2)
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 0
    assert int(dut.scan_active.value) == 1
