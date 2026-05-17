#!/usr/bin/env python3
from pathlib import Path
import sys

import yaml


REQUIRED = [
    "docs/spec-db/mobile-sota-2026.yaml",
    "docs/benchmarks/benchmark-matrix.md",
    "docs/benchmarks/report-schema.yaml",
    "docs/android/riscv-bringup.md",
    "docs/project/three-week-execution-plan.md",
    "docs/project/workstreams.md",
    "docs/toolchain/README.md",
    "docs/risks/risk-register.md",
    "rtl/open_rtl_prototype_path.md",
    "board/README.md",
    "board/fpga/README.md",
    "board/fpga/hello_demo_fpga.yaml",
    "board/fpga/constraints/hello_demo_ulx3s.lpf",
    "fw/board-smoke/tests/smoke_plan.md",
    "docs/toolchain/headless-cli-audit.md",
]

REQUIRED_TERMS = {
    "docs/spec-db/mobile-sota-2026.yaml": [
        "snapdragon_8_elite_gen_5",
        "dimensity_9500",
        "explicit_non_goals",
    ],
    "docs/benchmarks/benchmark-matrix.md": [
        "Claim Levels",
        "MLPerf Mobile",
        "Never compare simulator wall-clock time",
    ],
    "docs/android/riscv-bringup.md": [
        "AOSP RISC-V",
        "TH1520",
        "Explicit v0 exclusions",
    ],
    "docs/project/three-week-execution-plan.md": [
        "Week 1",
        "Week 2",
        "Week 3",
        "Ten-Minute Operating Loop",
    ],
    "docs/project/workstreams.md": [
        "Parallel Workstreams",
        "Agent Queue",
        "Completion Bar",
    ],
    "docs/toolchain/README.md": [
        "CLI/headless audit matrix",
        "kicad-cli",
        "benchmark_model",
        "sigrok-cli",
    ],
    "docs/risks/risk-register.md": [
        "Drop-in flagship pin compatibility",
        "LPDDR5X",
        "v0 Non-Goals",
    ],
    "docs/benchmarks/report-schema.yaml": [
        "openphone.benchmark_report.v1",
        "claim_level",
        "Simulator wall-clock time",
    ],
    "rtl/open_rtl_prototype_path.md": [
        "Chipyard",
        "Rocket",
        "FireSim",
    ],
    "board/README.md": [
        "contract artifact",
        "not a manufacturable PCB yet",
        "must not be released for fabrication",
    ],
    "board/fpga/README.md": [
        "hello_demo_fpga",
        "make fpga-check",
        "Bitstream generation must remain blocked",
    ],
    "board/fpga/constraints/hello_demo_ulx3s.lpf": [
        "CLK_IN",
        "RST_N",
        "DBG_VALID",
        "GPIO",
    ],
    "fw/board-smoke/tests/smoke_plan.md": [
        "bring-up",
        "power",
        "GPIO",
    ],
    "docs/toolchain/headless-cli-audit.md": [
        "Headless CLI Audit",
        "kicad-cli",
        "docker run --rm",
        "No milestone may be marked complete",
    ],
}


def check_benchmark_schema(root: Path) -> list[str]:
    errors: list[str] = []
    schema_path = root / "docs/benchmarks/report-schema.yaml"
    matrix_path = root / "docs/benchmarks/benchmark-matrix.md"
    data = yaml.safe_load(schema_path.read_text())
    matrix = matrix_path.read_text()

    if data.get("schema") != "openphone.benchmark_report.v1":
        errors.append("docs/benchmarks/report-schema.yaml has an unexpected schema id")

    claim_levels = data.get("required_fields", {}).get("claim_level", {}).get("enum", [])
    expected_levels = [
        "L0_RTL_UNIT",
        "L1_RTL_FULL_SOC",
        "L2_ARCH_SIM",
        "L3_FPGA",
        "L4_DEV_BOARD",
        "L5_PROTOTYPE_SILICON",
        "L6_COMPLETE_PHONE",
    ]
    missing_levels = [level for level in expected_levels if level not in claim_levels]
    if missing_levels:
        errors.append(
            "docs/benchmarks/report-schema.yaml is missing claim levels: "
            + ", ".join(missing_levels)
        )

    required_fields = data.get("required_fields", {})
    for field in ("platform", "workload", "software", "clocks", "memory", "thermal", "power", "results", "artifacts"):
        if field not in required_fields:
            errors.append(f"docs/benchmarks/report-schema.yaml missing required field block: {field}")

    required_rules = [
        "Simulator wall-clock time must not be compared against commercial phone scores.",
        "NPU reports must include unsupported op count and CPU fallback percentage.",
        "Android reports must separate boot success from CTS/VTS compatibility.",
    ]
    rules = data.get("validation_rules", [])
    for rule in required_rules:
        if rule not in rules:
            errors.append(f"docs/benchmarks/report-schema.yaml missing validation rule: {rule}")

    for token in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "coremark", "stream", "tflite"):
        if token not in matrix:
            errors.append(f"docs/benchmarks/benchmark-matrix.md missing benchmark token: {token}")

    return errors


def check_android_plan(root: Path) -> list[str]:
    errors: list[str] = []
    text = (root / "docs/android/riscv-bringup.md").read_text()
    required = [
        "sw/platform/hello_platform_contract.json",
        "make aosp-bsp-check",
        "CTS/VTS",
        "SELinux denials",
        "command transcript",
    ]
    for term in required:
        if term not in text:
            errors.append(f"docs/android/riscv-bringup.md missing Android evidence term: {term}")

    aosp_artifacts = [
        "sw/aosp-device/device/openphone/openphone_ai_soc/BoardConfig.mk",
        "sw/aosp-device/device/openphone/openphone_ai_soc/device.mk",
        "sw/aosp-device/device/openphone/openphone_ai_soc/init.openphone.rc",
        "sw/aosp-device/device/openphone/openphone_ai_soc/manifest.xml",
        "sw/aosp-device/device/openphone/openphone_ai_soc/sepolicy/file_contexts",
    ]
    missing = [path for path in aosp_artifacts if not (root / path).is_file()]
    if missing:
        errors.append("Android project plan references missing BSP artifacts: " + ", ".join(missing))

    return errors


def check_board_plan(root: Path) -> list[str]:
    errors: list[str] = []
    cfg_path = root / "board/fpga/hello_demo_fpga.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())

    if cfg.get("target") != "hello_demo_fpga":
        errors.append("board/fpga/hello_demo_fpga.yaml must target hello_demo_fpga")
    if cfg.get("status") != "scaffold":
        errors.append("board/fpga/hello_demo_fpga.yaml must remain status: scaffold")
    if cfg.get("rtl_top") != "hello_chip_top":
        errors.append("board/fpga/hello_demo_fpga.yaml must point at hello_chip_top")
    if cfg.get("constraints", {}).get("bitstream_release_blocked_until_pins_assigned") is not True:
        errors.append("FPGA plan must block bitstream release until pins are assigned")
    if cfg.get("board", {}).get("exact_revision") != "unassigned":
        errors.append("FPGA board revision should stay unassigned until a real board is selected")

    required_ports = {
        cfg.get("clock", {}).get("port"),
        cfg.get("reset", {}).get("port"),
        cfg.get("external_outputs", {}).get("gpio_port"),
        *cfg.get("debug_bridge", {}).get("required_ports", []),
        *cfg.get("external_outputs", {}).get("irq_ports", []),
    }
    required_ports.discard(None)
    constraint_path = root / cfg.get("constraints", {}).get("skeleton_lpf", "")
    constraint_text = constraint_path.read_text(errors="ignore") if constraint_path.is_file() else ""
    missing_mentions = sorted(port for port in required_ports if port not in constraint_text)
    if missing_mentions:
        errors.append("FPGA constraint skeleton missing required signal mentions: " + ", ".join(missing_mentions))

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        print("Missing project plan artifacts:")
        for path in missing:
            print(f"  - {path}")
        return 1

    for path, terms in REQUIRED_TERMS.items():
        text = (root / path).read_text()
        absent = [term for term in terms if term not in text]
        if absent:
            print(f"{path} is missing required terms: {', '.join(absent)}")
            return 1
        if "TODO" in text:
            print(f"{path} still contains TODO")
            return 1

    errors = []
    errors.extend(check_benchmark_schema(root))
    errors.extend(check_android_plan(root))
    errors.extend(check_board_plan(root))
    if errors:
        print("Project plan artifact checks failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("project plan artifacts present and structurally checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
