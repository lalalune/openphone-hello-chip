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


async def poll_done(dut, cycles=32):
    for _ in range(cycles):
        status = await read_reg(dut, 3)
        if status & 0x2:
            return status
    raise AssertionError("timeout waiting for NPU operation")


async def write_scratch_word(dut, word, value):
    await write_reg(dut, 0x20 + word, value)


async def read_scratch_s32(dut, byte_offset):
    assert byte_offset % 4 == 0
    value = await read_reg(dut, 0x20 + byte_offset // 4)
    if value & 0x8000_0000:
        return value - 0x1_0000_0000
    return value


async def run_scalar(dut, opcode, op_a, op_b, acc=0):
    await write_reg(dut, 3, 2)
    await write_reg(dut, 0, op_a)
    await write_reg(dut, 1, op_b)
    await write_reg(dut, 5, acc)
    await write_reg(dut, 4, opcode)
    await write_reg(dut, 3, 1)
    assert await poll_done(dut) == 0x2
    return await read_reg(dut, 2), await read_reg(dut, 6)


def pack_s8(values):
    word = 0
    for index, value in enumerate(values):
        word |= (value & 0xFF) << (8 * index)
    return word


def pack_s4(values):
    word = 0
    for index, value in enumerate(values):
        word |= (value & 0xF) << (4 * index)
    return word


def pack_bytes(values):
    word = 0
    for index, value in enumerate(values):
        word |= (value & 0xFF) << (8 * index)
    return word


@cocotb.test()
async def npu_scalar_opcodes_match_expected_results(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    result, result_hi = await run_scalar(dut, 0, 0xFFFF_FFFF, 2)
    assert result == 1
    assert result_hi == 0

    result, result_hi = await run_scalar(dut, 1, 3, 5)
    assert result == 0xFFFF_FFFE
    assert result_hi == 0

    result, result_hi = await run_scalar(dut, 2, 0xFFFF_FFFF, 2)
    assert result == 0xFFFF_FFFE
    assert result_hi == 1

    result, result_hi = await run_scalar(dut, 3, 0x0000_FFFE, 7, 20)
    assert result == 6
    assert result_hi == 0

    result, result_hi = await run_scalar(
        dut,
        4,
        pack_s8([1, -2, 3, -4]),
        pack_s8([5, 6, -7, -8]),
        9,
    )
    assert result == 13
    assert result_hi == 0

    result, _ = await run_scalar(dut, 5, 0x8000_0000, 0x7FFF_FFFF)
    assert result == 0x8000_0000

    result, _ = await run_scalar(dut, 6, 0x8000_0000, 0x7FFF_FFFF)
    assert result == 0x7FFF_FFFF

    result, result_hi = await run_scalar(
        dut,
        7,
        pack_s4([1, 2, 3, 4, 5, 6, 7, -8]),
        pack_s4([1, 1, 1, 1, 1, 1, 1, -1]),
        4,
    )
    assert result == 40
    assert result_hi == 0

    result, result_hi = await run_scalar(
        dut,
        7,
        pack_s4([-8, -7, -6, -5, -4, -3, -2, -1]),
        pack_s4([1, 1, 1, 1, 1, 1, 1, 1]),
        0,
    )
    assert result == 0xFFFF_FFDC
    assert result_hi == 0xFFFF_FFFF


@cocotb.test()
async def npu_rejects_invalid_opcode_and_clears_error_irq(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 4, 0xF)
    assert await read_reg(dut, 4) == 0xF
    await write_reg(dut, 3, 1)
    assert await poll_done(dut) == 0x6
    assert int(dut.irq.value) == 1
    assert await read_reg(dut, 0x0B) == 1
    assert await read_reg(dut, 0x17) == 1

    await write_reg(dut, 3, 2)
    assert await read_reg(dut, 3) == 0
    assert int(dut.irq.value) == 0


@cocotb.test()
async def npu_busy_launch_is_ignored_until_current_operation_completes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0, 0xFFFF_FFFF)
    await write_reg(dut, 1, 0xFFFF_FFFE)
    await write_reg(dut, 4, 2)
    await write_reg(dut, 3, 1)
    busy = await read_reg(dut, 7)
    assert busy & 0x7

    await write_reg(dut, 3, 1)
    assert await poll_done(dut) == 0x2
    assert await read_reg(dut, 2) == 2
    assert await read_reg(dut, 6) == 0xFFFF_FFFD

    await write_reg(dut, 0, 10)
    await write_reg(dut, 1, 20)
    await write_reg(dut, 4, 0)
    await write_reg(dut, 3, 1)

    assert await poll_done(dut) == 0x2
    assert await read_reg(dut, 2) == 30
    assert await read_reg(dut, 6) == 0


@cocotb.test()
async def npu_gemm_invalid_config_reports_error_without_touching_scratch(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0x20, 0xA5A5_5A5A)
    await write_reg(dut, 0x08, 0)  # zero dimensions are invalid
    await write_reg(dut, 0x09, 0)
    await write_reg(dut, 0x0A, 0)
    await write_reg(dut, 0x04, 8)
    await write_reg(dut, 0x03, 1)

    assert await poll_done(dut) == 0x6
    assert await read_reg(dut, 0x0B) == 1
    assert await read_reg(dut, 0x17) == 1
    assert await read_reg(dut, 0x20) == 0xA5A5_5A5A

    await write_reg(dut, 0x17, 1)
    assert await read_reg(dut, 0x0B) == 0
    assert await read_reg(dut, 0x17) == 0


@cocotb.test()
async def npu_gemm_s8_2x2x3_writes_expected_scratch_and_perf(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    # A = [[1, -2, 3], [4, 5, -6]]
    # B = [[7, -8], [9, 10], [-11, 12]]
    await write_scratch_word(dut, 0, pack_bytes([1, -2, 3, 4]))
    await write_scratch_word(dut, 1, pack_bytes([5, -6, 7, -8]))
    await write_scratch_word(dut, 2, pack_bytes([9, 10, -11, 12]))
    await write_scratch_word(dut, 3, 0)
    await write_scratch_word(dut, 4, 0)
    await write_scratch_word(dut, 5, 0)
    await write_scratch_word(dut, 6, 0)

    await write_reg(dut, 0x17, 1)
    await write_reg(dut, 0x08, 2 | (2 << 8) | (3 << 16))
    await write_reg(dut, 0x09, 0 | (6 << 8) | (12 << 16))
    await write_reg(dut, 0x0A, 3 | (2 << 8) | (8 << 16))
    await write_reg(dut, 0x04, 8)
    await write_reg(dut, 0x03, 1)

    assert await poll_done(dut, cycles=64) == 0x2
    assert await read_scratch_s32(dut, 12) == -44
    assert await read_scratch_s32(dut, 16) == 8
    assert await read_scratch_s32(dut, 20) == 139
    assert await read_scratch_s32(dut, 24) == -54
    assert await read_reg(dut, 0x14) == 12
    assert await read_reg(dut, 0x15) == 12
    assert await read_reg(dut, 0x16) == 1
    assert await read_reg(dut, 0x17) == 0
