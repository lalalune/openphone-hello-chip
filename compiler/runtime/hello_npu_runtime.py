class HelloNpuRuntime:
    """Reference runtime for the hello NPU MMIO contract."""

    OP_A = 0x1002_0000
    OP_B = 0x1002_0004
    RESULT = 0x1002_0008
    CTRL_STATUS = 0x1002_000C
    OPCODE = 0x1002_0010
    ACC = 0x1002_0014
    RESULT_HI = 0x1002_0018

    OP_ADD = 0
    OP_SUB = 1
    OP_MUL_LO = 2
    OP_MAC_S16 = 3
    OP_DOT4_S8 = 4
    OP_MAX_U32 = 5
    OP_MIN_U32 = 6

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
