import json
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

REPO_ROOT = Path(__file__).resolve().parents[2]


async def reset(dut):
    dut.rst_n.value = 0
    dut.valid.value = 0
    dut.write.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    dut.fb_read_data.value = 0
    dut.fb_read_ready.value = 0
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


def write_coverage_artifact(extra):
    coverage = {
        "schema": "hello-chip.display_cocotb_coverage.v1",
        "source": "verify/cocotb/test_hello_display.py",
        "covered_contracts": sorted(extra),
        "pixel_format": "XR24 only",
        "boundary": "Directed hello_display MMIO, XR24 scanout, underflow, and timing checks only; no DRM/KMS, HDMI/MIPI, compositor, or display PHY coverage.",
    }
    out = REPO_ROOT / "build/reports/display_cocotb_coverage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    assert int(dut.fb_read_valid.value) == 0
    assert int(dut.fb_read_addr.value) == 0


@cocotb.test()
async def display_clamps_mode_and_rejects_unsupported_format(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 1, 0)
    assert await read_reg(dut, 1) == (1 << 16) | 1

    await write_reg(dut, 2, 0x3432_4247)  # XB24/GB24-like value is rejected.
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

    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00112233
    await Timer(1, units="ns")
    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 0
    assert int(dut.scan_fb_addr.value) == 0x8000_0000
    assert int(dut.fb_read_valid.value) == 1
    assert int(dut.fb_read_addr.value) == 0x8000_0000
    assert int(dut.scan_rgb.value) == 0x112233

    dut.fb_read_data.value = 0x00A0B0C0
    await advance(dut, 1)
    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_x.value) == 1
    assert int(dut.scan_fb_addr.value) == 0x8000_0004
    assert int(dut.fb_read_addr.value) == 0x8000_0004
    assert int(dut.scan_rgb.value) == 0xA0B0C0

    await advance(dut, 3)
    assert int(dut.scan_active.value) == 0
    assert int(dut.scan_x.value) == 4
    assert int(dut.scan_fb_addr.value) == 0
    assert int(dut.fb_read_valid.value) == 0
    assert int(dut.fb_read_addr.value) == 0

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


@cocotb.test()
async def display_counts_fetched_pixels_and_underflows(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0, 0x8000_0100)
    await write_reg(dut, 1, (2 << 16) | 3)
    await write_reg(dut, 3, 1)

    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00010203
    await advance(dut, 1)

    dut.fb_read_ready.value = 0
    await Timer(1, units="ns")
    await advance(dut, 1)
    assert int(dut.scan_rgb.value) == 0
    assert await read_reg(dut, 5) == 1
    assert await read_reg(dut, 6) == 1

    await write_reg(dut, 5, 1)
    await write_reg(dut, 6, 1)
    assert await read_reg(dut, 5) == 0
    assert await read_reg(dut, 6) == 0


@cocotb.test()
async def display_delayed_framebuffer_response_underflows_then_recovers(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0, 0x8000_0200)
    await write_reg(dut, 1, (1 << 16) | 8)
    await write_reg(dut, 3, 1)

    dut.fb_read_ready.value = 0
    dut.fb_read_data.value = 0x00FF_0000
    await Timer(1, units="ns")
    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_rgb.value) == 0
    assert int(dut.fb_read_addr.value) == 0x8000_0200
    await advance(dut, 2)

    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x0000_8040
    await Timer(1, units="ns")
    assert int(dut.scan_active.value) == 1
    assert int(dut.scan_rgb.value) == 0x008040
    assert int(dut.fb_read_addr.value) == 0x8000_0208
    await advance(dut, 6)
    assert int(dut.scan_active.value) == 0
    assert await read_reg(dut, 5) == 2
    assert await read_reg(dut, 6) == 6


@cocotb.test()
async def display_reports_stride_and_frame_byte_count(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    assert await read_reg(dut, 7) == 640 * 4
    assert await read_reg(dut, 8) == 640 * 480 * 4
    assert await read_reg(dut, 9) == 0

    await write_reg(dut, 1, (3 << 16) | 4)
    assert await read_reg(dut, 7) == 16
    assert await read_reg(dut, 8) == 48
    assert await read_reg(dut, 9) == 0

    await write_reg(dut, 1, (0xFFFF << 16) | 0xFFFF)
    expected = 0xFFFF * 0xFFFF * 4
    assert await read_reg(dut, 7) == 0x3FFFC
    assert await read_reg(dut, 8) == (expected & 0xFFFF_FFFF)
    assert await read_reg(dut, 9) == (expected >> 32)


@cocotb.test()
async def display_disable_resets_scan_position_and_blocks_fetches(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    await write_reg(dut, 0, 0x8000_0400)
    await write_reg(dut, 1, (2 << 16) | 4)
    await write_reg(dut, 3, 1)
    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00AA_5500
    await advance(dut, 3)
    assert int(dut.scan_x.value) == 3
    assert int(dut.fb_read_valid.value) == 1

    await write_reg(dut, 3, 0)
    await Timer(1, units="ns")
    assert int(dut.scan_active.value) == 0
    assert int(dut.fb_read_valid.value) == 0
    assert int(dut.fb_read_addr.value) == 0
    assert int(dut.scan_fb_addr.value) == 0
    await advance(dut, 2)
    assert int(dut.scan_x.value) == 0
    assert int(dut.scan_y.value) == 0
    assert int(dut.irq_vsync.value) == 0

    write_coverage_artifact({"disable_fetch_gate", "scan_position_reset", "xr24_scanout"})


# ---------------------------------------------------------------------------
# Timing and recovery tests added in verification pass 2
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_display_frame_timing(dut):
    """Count cycles between consecutive VSYNC pulses; verify within ±2% of expected.

    Uses the small test mode (H=4+16+96+48=164, V=3+10+2+33=48).
    Expected frame period: 164 * 48 = 7872 cycles.  Tolerance: ±2% = ±157 cycles.
    """
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    # Small test mode matching existing timing tests
    await write_reg(dut, 0, 0x8000_0500)
    await write_reg(dut, 1, (3 << 16) | 4)   # height=3, width=4
    await write_reg(dut, 3, 1)                # enable

    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00FF_8040

    # Horizontal total: active(4) + fp(16) + sync(96) + bp(48) = 164
    # Vertical total:   active(3) + fp(10) + sync(2)  + bp(33) = 48
    total_h = 4 + 16 + 96 + 48
    total_v = 3 + 10 + 2 + 33
    expected_period = total_h * total_v  # 7872 cycles
    tolerance = int(expected_period * 0.02)  # 2% ≈ 157 cycles

    # Advance to the first VSYNC rising edge
    max_search = expected_period + 200
    got_vsync = False
    for _ in range(max_search):
        await RisingEdge(dut.clk)
        if int(dut.scan_vsync.value):
            got_vsync = True
            break
    assert got_vsync, "First VSYNC never arrived"

    # Wait for VSYNC to fall before starting the period measurement
    while int(dut.scan_vsync.value):
        await RisingEdge(dut.clk)

    # Count cycles until the next VSYNC rising edge
    cycle_count = 0
    while not int(dut.scan_vsync.value):
        await RisingEdge(dut.clk)
        cycle_count += 1

    assert abs(cycle_count - expected_period) <= tolerance, (
        f"Frame period {cycle_count} cycles differs from expected {expected_period} "
        f"by more than ±{tolerance} cycles (±2%)"
    )

    write_coverage_artifact({"frame_timing_within_2pct"})


@cocotb.test()
async def test_display_underflow_recovery(dut):
    """Stall memory for 100 cycles during active scan; verify underflow counter
    increments and the display recovers (VSYNC still fires) after stall ends.
    """
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    # Width=8, height=4 — enough active pixels to observe mid-scan stall
    await write_reg(dut, 0, 0x8000_0600)
    await write_reg(dut, 1, (4 << 16) | 8)   # height=4, width=8
    await write_reg(dut, 5, 1)               # clear underflow counter
    await write_reg(dut, 6, 1)               # clear pixel counter
    await write_reg(dut, 3, 1)               # enable

    # Supply valid pixel data initially
    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00AA_BB_CC
    await advance(dut, 2)

    # Stall: deassert fb_read_ready for 100 cycles
    dut.fb_read_ready.value = 0
    await advance(dut, 100)

    # Underflow counter must have incremented during the stall
    underflow_count = await read_reg(dut, 5)
    assert underflow_count > 0, (
        f"Underflow counter should be >0 after 100-cycle stall, got {underflow_count}"
    )

    # Restore memory
    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00FF_00_FF

    # Display must recover and produce at least one more VSYNC
    total_h = 8 + 16 + 96 + 48
    total_v = 4 + 10 + 2 + 33
    max_wait = total_h * total_v * 2
    vsync_seen = False
    for _ in range(max_wait):
        await RisingEdge(dut.clk)
        if int(dut.scan_vsync.value):
            vsync_seen = True
            break

    assert vsync_seen, (
        "Display did not recover: no VSYNC observed after 100-cycle underflow stall"
    )

    write_coverage_artifact({"underflow_recovery_after_stall"})


@cocotb.test()
async def test_display_mode_change(dut):
    """Change resolution mid-frame; verify no spurious pixels are emitted between
    disable and re-enable, and the new mode starts cleanly from x=0, y=0.
    """
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)

    # Start with width=4, height=2
    await write_reg(dut, 0, 0x8000_0700)
    await write_reg(dut, 1, (2 << 16) | 4)
    await write_reg(dut, 3, 1)

    dut.fb_read_ready.value = 1
    dut.fb_read_data.value = 0x00112233

    # Advance partway into the first active scanline
    await advance(dut, 2)
    assert int(dut.scan_active.value) == 1, "scan_active should be high mid-scanline"
    assert int(dut.scan_x.value) == 2

    # Disable mid-frame
    await write_reg(dut, 3, 0)
    await Timer(1, units="ns")

    # scan_active must drop immediately on disable
    assert int(dut.scan_active.value) == 0, "scan_active must be 0 immediately after disable"
    assert int(dut.fb_read_valid.value) == 0, "fb_read_valid must be 0 after disable"

    # Advance a few cycles — no spurious pixel activity
    spurious_active = False
    for _ in range(10):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if int(dut.scan_active.value):
            spurious_active = True
            break

    assert not spurious_active, "Spurious scan_active asserted after display disable"

    # Re-enable with new resolution: width=8, height=4
    await write_reg(dut, 1, (4 << 16) | 8)
    await write_reg(dut, 3, 1)
    await Timer(1, units="ns")

    # New mode must start from x=0, y=0
    assert int(dut.scan_x.value) == 0, "scan_x must be 0 at start of new mode"
    assert int(dut.scan_y.value) == 0, "scan_y must be 0 at start of new mode"
    assert int(dut.scan_active.value) == 1, "scan_active must be 1 at start of new mode"

    # Advance exactly <new_width> cycles and verify active region ends
    await advance(dut, 8)
    assert int(dut.scan_x.value) == 8, (
        f"scan_x={int(dut.scan_x.value)}, expected 8 after new-mode width pixels"
    )
    assert int(dut.scan_active.value) == 0, (
        "scan_active must be 0 after new-mode active width"
    )

    write_coverage_artifact({"mode_change_no_spurious_pixels"})
