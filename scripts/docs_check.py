from pathlib import Path

required = [
    "docs/arch/soc.md",
    "docs/arch/memory-map.md",
    "docs/arch/interrupts.md",
    "docs/arch/boot.md",
    "docs/arch/android-contract.md",
    "docs/arch/peripherals.md",
    "docs/arch/wifi.md",
    "docs/board/fpga/README.md",
    "docs/sim/qemu/README.md",
    "docs/sim/renode/README.md",
    "sw/platform/hello_platform_contract.json",
    "sw/platform/generated/hello_platform_contract.h",
    "docs/tapeout-checklist/hello-chip.md",
    "docs/toolchain/README.md",
]

missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing docs: " + ", ".join(missing))

for path in required:
    text = Path(path).read_text()
    if "TODO" in text:
        raise SystemExit(f"{path} still contains TODO")

print("docs skeleton present")
