import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


def lui(rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x37


def addi(rd, rs1, imm):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13


def add(rd, rs1, rs2):
    return (rs2 << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x33


def lw(rd, offset, rs1):
    imm = offset & 0xFFF
    return (imm << 20) | (rs1 << 15) | (2 << 12) | (rd << 7) | 0x03


def sw(rs2, offset, rs1):
    imm = offset & 0xFFF
    return (
        ((imm >> 5) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (2 << 12)
        | ((imm & 0x1F) << 7)
        | 0x23
    )


async def reset(dut):
    dut.rst_n.value = 0
    dut.cpu_enable.value = 0
    dut.loader_awvalid.value = 0
    dut.loader_awaddr.value = 0
    dut.loader_wvalid.value = 0
    dut.loader_wdata.value = 0
    dut.loader_wstrb.value = 0
    dut.loader_bready.value = 1
    dut.loader_arvalid.value = 0
    dut.loader_araddr.value = 0
    dut.loader_rready.value = 1
    dut.irq_sources.value = 0
    await Timer(1, units="ns")
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def axil_write32(dut, addr, data, strobe=0xF):
    dut.loader_awaddr.value = addr
    dut.loader_wdata.value = data
    dut.loader_wstrb.value = strobe
    dut.loader_awvalid.value = 1
    dut.loader_wvalid.value = 1
    dut.loader_bready.value = 1

    while True:
        await Timer(1, units="ns")
        if int(dut.loader_awready.value) and int(dut.loader_wready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    dut.loader_awvalid.value = 0
    dut.loader_wvalid.value = 0

    while True:
        await Timer(1, units="ns")
        if int(dut.loader_bvalid.value):
            resp = int(dut.loader_bresp.value)
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    return resp


async def axil_read32(dut, addr):
    dut.loader_araddr.value = addr
    dut.loader_arvalid.value = 1
    dut.loader_rready.value = 1

    while True:
        await Timer(1, units="ns")
        if int(dut.loader_arready.value):
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    dut.loader_arvalid.value = 0

    while True:
        await Timer(1, units="ns")
        if int(dut.loader_rvalid.value):
            data = int(dut.loader_rdata.value)
            resp = int(dut.loader_rresp.value)
            break
        await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    return data, resp


@cocotb.test()
async def tiny_cpu_fetches_executes_and_updates_soc_state(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    program = [
        lui(4, 0x80000),       # x4 = DRAM base
        addi(1, 0, 5),         # x1 = 5
        addi(2, 0, 7),         # x2 = 7
        add(3, 1, 2),          # x3 = 12
        sw(3, 0x100, 4),       # DRAM[0x80000100] = 12
        lui(5, 0x0C000),       # x5 = interrupt controller base
        addi(6, 0, 0b1010),    # enable sources 2 and 4
        sw(6, 0x008, 5),       # INTC.ENABLE = 0b1010
        0x00000073,            # ECALL: halt tiny core
    ]

    for index, instr in enumerate(program):
        assert await axil_write32(dut, 0x8000_0000 + index * 4, instr) == 0

    dut.cpu_enable.value = 1
    for _ in range(200):
        await RisingEdge(dut.clk)
        if int(dut.cpu_halted.value):
            break

    assert int(dut.cpu_halted.value) == 1

    dut.cpu_enable.value = 0
    await RisingEdge(dut.clk)

    data, resp = await axil_read32(dut, 0x8000_0100)
    assert resp == 0
    assert data == 12

    data, resp = await axil_read32(dut, 0x0C00_0008)
    assert resp == 0
    assert data & 0b1010 == 0b1010

    dut.irq_sources.value = 0b0010
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.cpu_external_irq.value) == 1


@cocotb.test()
async def tiny_cpu_halts_on_unsupported_instruction_and_fetch_error(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0000, 0xFFFF_FFFF) == 0

    dut.cpu_enable.value = 1
    for _ in range(32):
        await RisingEdge(dut.clk)
        if int(dut.cpu_halted.value):
            break
    assert int(dut.cpu_halted.value) == 1

    dut.cpu_enable.value = 0
    await RisingEdge(dut.clk)
    await reset(dut)

    program = [
        lui(1, 0x40000),       # x1 = unmapped fetch target
        0x00008067,            # JALR x0, 0(x1)
    ]
    for index, instr in enumerate(program):
        assert await axil_write32(dut, 0x8000_0000 + index * 4, instr) == 0

    dut.cpu_enable.value = 1
    for _ in range(64):
        await RisingEdge(dut.clk)
        if int(dut.cpu_halted.value):
            break
    assert int(dut.cpu_halted.value) == 1


@cocotb.test()
async def tiny_cpu_halts_on_unaligned_word_memory_before_bus_access(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await axil_write32(dut, 0x8000_0100, 0) == 0
    program = [
        lui(1, 0x80000),       # x1 = DRAM base
        addi(2, 0, 99),        # x2 = value that must not be stored
        sw(2, 0x102, 1),       # unaligned SW must halt locally
        0x00000073,            # ECALL would only execute if SW advanced
    ]
    for index, instr in enumerate(program):
        assert await axil_write32(dut, 0x8000_0000 + index * 4, instr) == 0

    dut.cpu_enable.value = 1
    for _ in range(80):
        await RisingEdge(dut.clk)
        if int(dut.cpu_halted.value):
            break
    assert int(dut.cpu_halted.value) == 1

    dut.cpu_enable.value = 0
    await RisingEdge(dut.clk)
    data, resp = await axil_read32(dut, 0x8000_0100)
    assert resp == 0
    assert data == 0

    await reset(dut)
    program = [
        lui(1, 0x80000),       # x1 = DRAM base
        lw(2, 0x102, 1),       # unaligned LW must halt locally
        sw(2, 0x100, 1),       # must not execute
    ]
    for index, instr in enumerate(program):
        assert await axil_write32(dut, 0x8000_0000 + index * 4, instr) == 0

    dut.cpu_enable.value = 1
    for _ in range(80):
        await RisingEdge(dut.clk)
        if int(dut.cpu_halted.value):
            break
    assert int(dut.cpu_halted.value) == 1
