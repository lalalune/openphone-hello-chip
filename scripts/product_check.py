from pathlib import Path
import argparse
import subprocess
import sys

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--release", action="store_true", help="fail on fabrication/tapeout release blockers")
args = parser.parse_args()

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
    "docs/manufacturing/real-world-verification-gaps.yaml",
    "docs/manufacturing/physical-closure-work-order.yaml",
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
subprocess.run([sys.executable, "scripts/check_physical_closure_work_order.py"], check=True)
subprocess.run([sys.executable, "scripts/check_pd_signoff.py", "--manifest-only"], check=True)
subprocess.run([sys.executable, "scripts/check_real_world_gates.py"], check=True)

release_blockers: list[str] = []

pinout = yaml.safe_load(Path("package/hello-demo-pinout.yaml").read_text())
package_name = str(pinout.get("package", ""))
pinout_notes = "\n".join(str(note) for note in pinout.get("notes", []))
if "placeholder" in package_name.lower() or "placeholder" in pinout_notes.lower():
    release_blockers.append("package pinout still declares a placeholder package")

for path in [
    "package/hello-demo-package.md",
    "package/hello-demo-pad-ring.md",
    "board/kicad/hello-demo/fab-notes.md",
]:
    text = Path(path).read_text().lower()
    if (
        "placeholder" in text
        or "not a foundry-approved" in text
        or "does not instantiate foundry pad cells" in text
    ):
        release_blockers.append(f"{path} is still a placeholder/draft artifact")

kicad_dir = Path("board/kicad/hello-demo")
kicad_required = {
    "project": list(kicad_dir.glob("*.kicad_pro")),
    "schematic": list(kicad_dir.glob("*.kicad_sch")),
    "pcb": list(kicad_dir.glob("*.kicad_pcb")),
}
for artifact, matches in kicad_required.items():
    if not matches:
        release_blockers.append(f"missing KiCad {artifact} artifact under {kicad_dir}")

fpga = yaml.safe_load(Path("board/fpga/hello_demo_fpga.yaml").read_text())
if fpga.get("status") != "release_ready":
    release_blockers.append(f"FPGA target status is {fpga.get('status')}, not release_ready")
if fpga.get("board", {}).get("exact_revision") in {None, "", "unassigned"}:
    release_blockers.append("FPGA board exact_revision is unassigned")
if fpga.get("constraints", {}).get("bitstream_release_blocked_until_pins_assigned") is True:
    release_blockers.append("FPGA bitstream release is explicitly blocked until pins are assigned")

constraint_path = Path(fpga["constraints"]["skeleton_lpf"])
assigned_locs = [
    line
    for line in constraint_path.read_text().splitlines()
    if line.strip().startswith("LOCATE COMP") and not line.lstrip().startswith("#")
]
if not assigned_locs:
    release_blockers.append(f"{constraint_path} has no concrete FPGA LOCATE COMP assignments")

pd_signoff = subprocess.run(
    [sys.executable, "scripts/check_pd_signoff.py"],
    check=False,
    text=True,
    capture_output=True,
)
if pd_signoff.returncode != 0:
    release_blockers.append("PD signoff artifacts/gates are incomplete; run scripts/check_pd_signoff.py for details")

if release_blockers:
    print("product release check failed:")
    for blocker in release_blockers:
        print(f"  - {blocker}")
    if pd_signoff.stdout:
        print("\nPD signoff detail:")
        print(pd_signoff.stdout.rstrip())
    if pd_signoff.stderr:
        print(pd_signoff.stderr.rstrip(), file=sys.stderr)
    if args.release:
        raise SystemExit(1)
    print("product artifact skeleton present; release blockers remain documented")
    raise SystemExit(0)

print("product release check ok")
