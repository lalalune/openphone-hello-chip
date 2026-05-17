class HelloNpuRuntime:
    """Reference runtime for the hello NPU MMIO contract."""

    OP_A = 0x1002_0000
    OP_B = 0x1002_0004
    RESULT = 0x1002_0008
    CTRL_STATUS = 0x1002_000C
    OPCODE = 0x1002_0010
    ACC = 0x1002_0014
    RESULT_HI = 0x1002_0018
    DEBUG = 0x1002_001C
    GEMM_CFG = 0x1002_0020
    GEMM_BASE = 0x1002_0024
    GEMM_STRIDE = 0x1002_0028
    PERF_UNSUPPORTED_OPS = 0x1002_002C
    CMD_PARAM = 0x1002_0030
    DESC_BASE = 0x1002_0040
    DESC_HEAD = 0x1002_0044
    DESC_TAIL = 0x1002_0048
    DESC_STATUS = 0x1002_004C
    PERF_CYCLES = 0x1002_0050
    PERF_MACS = 0x1002_0054
    PERF_OPS = 0x1002_0058
    PERF_ERRORS = 0x1002_005C
    SCRATCH = 0x1002_0080
    SCRATCH_BYTES = 64

    OP_ADD = 0
    OP_SUB = 1
    OP_MUL_LO = 2
    OP_MAC_S16 = 3
    OP_DOT4_S8 = 4
    OP_MAX_U32 = 5
    OP_MIN_U32 = 6
    OP_DOT8_S4 = 7
    OP_GEMM_S8 = 8

    def __init__(self, read32, write32):
        self.read32 = read32
        self.write32 = write32

    def run(self, opcode: int, a: int, b: int, acc: int = 0) -> int:
        self.write32(self.OP_A, a & 0xFFFF_FFFF)
        self.write32(self.OP_B, b & 0xFFFF_FFFF)
        self.write32(self.ACC, acc & 0xFFFF_FFFF)
        self.write32(self.OPCODE, opcode & 0xF)
        self.write32(self.CTRL_STATUS, 2)
        self.write32(self.CTRL_STATUS, 1)
        for _ in range(1024):
            status = self.read32(self.CTRL_STATUS)
            if status & 0x4:
                raise RuntimeError("hello NPU rejected command")
            if status & 0x2:
                return self.read32(self.RESULT)
        raise TimeoutError("hello NPU command did not complete")

    def add(self, a: int, b: int) -> int:
        return self.run(self.OP_ADD, a, b)

    def sub(self, a: int, b: int) -> int:
        return self.run(self.OP_SUB, a, b)

    def mul_lo(self, a: int, b: int) -> int:
        return self.run(self.OP_MUL_LO, a, b)

    def mac_s16(self, a: int, b: int, acc: int = 0) -> int:
        return self.run(self.OP_MAC_S16, a, b, acc)

    def dot4_s8(self, a_packed: int, b_packed: int, acc: int = 0) -> int:
        return self.run(self.OP_DOT4_S8, a_packed, b_packed, acc)

    def dot8_s4(self, a_packed: int, b_packed: int, acc: int = 0) -> int:
        return self.run(self.OP_DOT8_S4, a_packed, b_packed, acc)

    def clear_perf(self):
        self.write32(self.PERF_ERRORS, 1)

    def perf(self) -> dict:
        return {
            "cycles": self.read32(self.PERF_CYCLES),
            "macs": self.read32(self.PERF_MACS),
            "ops": self.read32(self.PERF_OPS),
            "errors": self.read32(self.PERF_ERRORS),
            "unsupported_ops": self.read32(self.PERF_UNSUPPORTED_OPS),
        }

    def write_scratch(self, offset: int, data: bytes):
        if offset < 0 or offset + len(data) > self.SCRATCH_BYTES:
            raise ValueError("scratch write exceeds 64-byte NPU scratchpad")
        if not data:
            return
        first_word = offset // 4
        last_word = (offset + len(data) - 1) // 4
        base = first_word * 4
        padded = bytearray()
        for word in range(first_word, last_word + 1):
            padded.extend(self.read32(self.SCRATCH + word * 4).to_bytes(4, "little"))
        relative_offset = offset - base
        padded[relative_offset : relative_offset + len(data)] = data
        for word in range(first_word, last_word + 1):
            start = (word - first_word) * 4
            value = int.from_bytes(padded[start : start + 4], "little")
            self.write32(self.SCRATCH + word * 4, value)

    def read_scratch(self, offset: int, size: int) -> bytes:
        if offset < 0 or offset + size > self.SCRATCH_BYTES:
            raise ValueError("scratch read exceeds 64-byte NPU scratchpad")
        if size == 0:
            return b""
        first_word = offset // 4
        last_word = (offset + size - 1) // 4
        data = bytearray()
        for word in range(first_word, last_word + 1):
            data.extend(self.read32(self.SCRATCH + word * 4).to_bytes(4, "little"))
        relative_offset = offset - first_word * 4
        return bytes(data[relative_offset : relative_offset + size])

    def gemm_s8(self, a, b):
        """Run bounded INT8 GEMM, returning an MxN int32 matrix.

        Prototype limits are M,N <= 3 and K <= 7, constrained by the 64-byte
        MMIO scratchpad. Inputs are Python integers interpreted as signed INT8.
        """
        m = len(a)
        k = len(a[0]) if m else 0
        n = len(b[0]) if b else 0
        if not (1 <= m <= 3 and 1 <= n <= 3 and 1 <= k <= 7):
            raise ValueError("GEMM dimensions exceed prototype limits")
        if any(len(row) != k for row in a) or len(b) != k or any(len(row) != n for row in b):
            raise ValueError("ragged GEMM inputs")

        a_base = 0
        b_base = m * k
        c_base = (b_base + k * n + 3) & ~3
        c_bytes = m * n * 4
        if c_base + c_bytes > self.SCRATCH_BYTES:
            raise ValueError("GEMM tile exceeds 64-byte NPU scratchpad")

        def s8(value):
            if not -128 <= value <= 127:
                raise ValueError("GEMM input outside signed INT8 range")
            return value & 0xFF

        a_bytes = bytes(s8(value) for row in a for value in row)
        b_bytes = bytes(s8(b[row][col]) for row in range(k) for col in range(n))

        self.clear_perf()
        self.write_scratch(a_base, a_bytes)
        self.write_scratch(b_base, b_bytes)
        self.write_scratch(c_base, bytes(c_bytes))
        self.write32(self.GEMM_CFG, m | (n << 8) | (k << 16))
        self.write32(self.GEMM_BASE, a_base | (b_base << 8) | (c_base << 16))
        self.write32(self.GEMM_STRIDE, k | (n << 8) | ((n * 4) << 16))
        self.write32(self.OPCODE, self.OP_GEMM_S8)
        self.write32(self.CTRL_STATUS, 2)
        self.write32(self.CTRL_STATUS, 1)
        for _ in range(1024):
            status = self.read32(self.CTRL_STATUS)
            if status & 0x4:
                raise RuntimeError("hello NPU rejected GEMM command")
            if status & 0x2:
                raw = self.read_scratch(c_base, c_bytes)
                return [
                    [
                        int.from_bytes(
                            raw[(r * n + c) * 4 : (r * n + c + 1) * 4], "little", signed=True
                        )
                        for c in range(n)
                    ]
                    for r in range(m)
                ]
        raise TimeoutError("hello NPU GEMM command did not complete")


def golden_gemm_s8(a, b):
    m = len(a)
    k = len(a[0]) if m else 0
    n = len(b[0]) if b else 0
    return [[sum(a[i][kk] * b[kk][j] for kk in range(k)) for j in range(n)] for i in range(m)]
