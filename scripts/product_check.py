from pathlib import Path
import subprocess
import sys

required = [
    "package/hello-demo-pinout.yaml",
    "package/hello-demo-package.md",
    "package/hello-demo-pad-ring.md",
    "pd/padframe/hello_demo_padframe.md",
    "pd/pin_order.cfg",
    "board/README.md",
    "board/kicad/hello-demo/fab-notes.md",
    "fw/board-smoke/tests/smoke_plan.md",
    "docs/manufacturing/hello-demo-checklist.md",
    "docs/manufacturing/release-manifest.yaml",
]

missing = [p for p in required if not Path(p).exists()]
if missing:
    raise SystemExit("missing product artifacts: " + ", ".join(missing))

subprocess.run(
    [sys.executable, "package/scripts/validate_pinout_vs_rtl.py"],
    check=True,
)

print("product artifact skeleton present")
