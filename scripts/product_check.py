from pathlib import Path
import subprocess
import sys

required = [
    "package/hello-demo-pinout.yaml",
    "package/hello-demo-package.md",
    "package/hello-demo-pad-ring.md",
    "package/wifi-external-interface.yaml",
    "pd/padframe/hello_demo_padframe.md",
    "pd/padframe/hello_demo_padframe.yaml",
    "pd/pin_order.cfg",
    "pd/signoff/manifest.yaml",
    "board/README.md",
    "board/fpga/README.md",
    "board/fpga/hello_demo_fpga.yaml",
    "board/fpga/constraints/hello_demo_ulx3s.lpf",
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
subprocess.run([sys.executable, "scripts/check_fpga_target.py"], check=True)
subprocess.run([sys.executable, "scripts/check_wifi_interface.py"], check=True)
subprocess.run([sys.executable, "scripts/check_padframe_contract.py"], check=True)
subprocess.run([sys.executable, "scripts/check_pd_signoff.py", "--manifest-only"], check=True)

print("product artifact skeleton present")
