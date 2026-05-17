#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hello_npu_runtime import HelloNpuRuntime, golden_gemm_s8


class HelloNpuMmioSim:
    """Tiny behavioral MMIO model for userspace runtime smoke tests."""

    def __init__(self):
        self.runtime = HelloNpuRuntime(self.read32, self.write32)
        self.regs: dict[int, int] = {
            self.runtime.CTRL_STATUS: 0,
            self.runtime.PERF_UNSUPPORTED_OPS: 0,
            self.runtime.PERF_CYCLES: 0,
            self.runtime.PERF_MACS: 0,
            self.runtime.PERF_OPS: 0,
            self.runtime.PERF_ERRORS: 0,
        }
        for word in range(self.runtime.SCRATCH_BYTES // 4):
            self.regs[self.runtime.SCRATCH + word * 4] = 0

    def read32(self, addr: int) -> int:
        return self.regs.get(addr, 0) & 0xFFFF_FFFF

    def write32(self, addr: int, value: int) -> None:
        value &= 0xFFFF_FFFF
        if addr == self.runtime.PERF_ERRORS and value & 1:
            for reg in (
                self.runtime.PERF_UNSUPPORTED_OPS,
                self.runtime.PERF_CYCLES,
                self.runtime.PERF_MACS,
                self.runtime.PERF_OPS,
                self.runtime.PERF_ERRORS,
            ):
                self.regs[reg] = 0
            return
        if addr == self.runtime.CTRL_STATUS and value & 2:
            self.regs[self.runtime.CTRL_STATUS] = 0
            return
        self.regs[addr] = value
        if addr == self.runtime.CTRL_STATUS and value & 1:
            self._execute()

    def _scratch_read_s8(self, offset: int) -> int:
        word = self.regs[self.runtime.SCRATCH + (offset & ~3)]
        value = (word >> (8 * (offset & 3))) & 0xFF
        return value - 0x100 if value & 0x80 else value

    def _scratch_write_s32(self, offset: int, value: int) -> None:
        self.regs[self.runtime.SCRATCH + offset] = value & 0xFFFF_FFFF

    def _execute(self) -> None:
        opcode = self.regs.get(self.runtime.OPCODE, 0)
        self.regs[self.runtime.PERF_OPS] += 1
        if opcode == self.runtime.OP_DOT8_S4:
            self.regs[self.runtime.RESULT] = 0
            self.regs[self.runtime.RESULT_HI] = 0
            self.regs[self.runtime.CTRL_STATUS] = 0x2
            return
        if opcode != self.runtime.OP_GEMM_S8:
            self.regs[self.runtime.PERF_UNSUPPORTED_OPS] += 1
            self.regs[self.runtime.PERF_ERRORS] += 1
            self.regs[self.runtime.CTRL_STATUS] = 0x6
            return

        cfg = self.regs[self.runtime.GEMM_CFG]
        bases = self.regs[self.runtime.GEMM_BASE]
        strides = self.regs[self.runtime.GEMM_STRIDE]
        m = cfg & 0x3
        n = (cfg >> 8) & 0x3
        k = (cfg >> 16) & 0x7
        a_base = bases & 0x3F
        b_base = (bases >> 8) & 0x3F
        c_base = (bases >> 16) & 0x3F
        a_stride = strides & 0xF
        b_stride = (strides >> 8) & 0xF
        c_stride = (strides >> 16) & 0xF
        macs = 0
        for row in range(m):
            for col in range(n):
                acc = 0
                for kk in range(k):
                    acc += self._scratch_read_s8(
                        a_base + row * a_stride + kk
                    ) * self._scratch_read_s8(b_base + kk * b_stride + col)
                    macs += 1
                self._scratch_write_s32(c_base + row * c_stride + col * 4, acc)
        self.regs[self.runtime.PERF_CYCLES] += macs
        self.regs[self.runtime.PERF_MACS] += macs
        self.regs[self.runtime.CTRL_STATUS] = 0x2


class HelloNpuRuntimeSimTest(unittest.TestCase):
    def test_runtime_gemm_s8_matches_golden_and_reports_perf(self):
        sim = HelloNpuMmioSim()
        a = [[1, -2, 3], [4, 5, -6]]
        b = [[7, -8], [9, 10], [-11, 12]]

        self.assertEqual(sim.runtime.gemm_s8(a, b), golden_gemm_s8(a, b))
        self.assertEqual(
            sim.runtime.perf(),
            {
                "cycles": 12,
                "macs": 12,
                "ops": 1,
                "errors": 0,
                "unsupported_ops": 0,
            },
        )

    def test_runtime_rejects_tiles_outside_local_prototype_limits(self):
        sim = HelloNpuMmioSim()
        with self.assertRaisesRegex(ValueError, "prototype limits"):
            sim.runtime.gemm_s8(
                [[1, 2, 3, 4, 5, 6, 7, 8]], [[1], [1], [1], [1], [1], [1], [1], [1]]
            )


if __name__ == "__main__":
    unittest.main()
