class HelloNpuRuntime:
    """Reference runtime for the hello NPU MMIO contract."""

    OP_A = 0x1002_0000
    OP_B = 0x1002_0004
    RESULT = 0x1002_0008
    CTRL_STATUS = 0x1002_000C

    def __init__(self, read32, write32):
        self.read32 = read32
        self.write32 = write32

    def add(self, a: int, b: int) -> int:
        self.write32(self.OP_A, a & 0xFFFF_FFFF)
        self.write32(self.OP_B, b & 0xFFFF_FFFF)
        self.write32(self.CTRL_STATUS, 1)
        for _ in range(1024):
            if self.read32(self.CTRL_STATUS) & 0x2:
                return self.read32(self.RESULT)
        raise TimeoutError("hello NPU command did not complete")
