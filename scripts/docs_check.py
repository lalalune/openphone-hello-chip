from pathlib import Path

required = [
    "arch/soc.md",
    "arch/memory-map.md",
    "arch/interrupts.md",
    "arch/boot.md",
    "arch/android-contract.md",
    "docs/tapeout-checklist/hello-chip.md",
]

missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing docs: " + ", ".join(missing))

for path in required:
    text = Path(path).read_text()
    if "TODO" in text:
        raise SystemExit(f"{path} still contains TODO")

print("docs skeleton present")
