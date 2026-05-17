#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml

REQUIRED_GROUPS = {
    "sdio": {
        "WIFI_SDIO_CLK",
        "WIFI_SDIO_CMD",
        "WIFI_SDIO_D0",
        "WIFI_SDIO_D1",
        "WIFI_SDIO_D2",
        "WIFI_SDIO_D3",
    },
    "control": {"WIFI_EN", "WIFI_RST_N"},
    "wake_irq": {"WIFI_HOST_WAKE", "WIFI_IRQ"},
    "bluetooth_uart": {"BT_UART_TX", "BT_UART_RX", "BT_UART_CTS_N", "BT_UART_RTS_N"},
}

REQUIRED_INTEGRATION_STATE = {
    "rtl_host_controller": "not_implemented",
    "gpio_pinctrl_regulator": "not_implemented",
    "padframe_bonding": "not_bonded_in_hello_chip",
    "firmware_driver": "not_implemented",
    "android_framework": "not_enabled",
    "rf_certification": "module_and_board_responsibility",
}

REFERENCE_MODULE = "package/wifi/murata-1dx-sdio.yaml"
EVIDENCE_MANIFEST = "package/wifi/evidence-gates.yaml"
REQUIRED_RELEASE_BLOCKERS = {
    "wifi_sdio_host": "SDIO host",
    "wifi_bt_uart": "BT UART",
    "wifi_firmware_provenance": "firmware provenance",
    "wifi_android_framework_logs": "Android framework logs",
    "wifi_regulatory_evidence": "regulatory evidence",
    "wifi_board_power_sequencing": "board/power sequencing",
}
REFERENCE_SIGNALS = {
    "WIFI_SDIO_CLK",
    "WIFI_SDIO_CMD",
    "WIFI_SDIO_D0",
    "WIFI_SDIO_D1",
    "WIFI_SDIO_D2",
    "WIFI_SDIO_D3",
    "WIFI_EN",
    "WIFI_RST_N",
    "WIFI_HOST_WAKE",
    "WIFI_IRQ",
    "BT_UART_TX",
    "BT_UART_RX",
    "BT_UART_CTS_N",
    "BT_UART_RTS_N",
}

ALLOWED_DIRECTIONS = {"input", "output", "bidirectional"}
ALLOWED_PULLS = {"none", "up", "down"}
ALLOWED_RESETS = {"input", "low", "high"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "package/wifi-external-interface.yaml"
    contract = yaml.safe_load(path.read_text())
    failures: list[str] = []

    if contract.get("io_voltage") != "1.8V":
        failures.append("WiFi interface must default to 1.8V IO")
    if contract.get("regulatory_boundary") != "module_and_board":
        failures.append("regulatory boundary must stay with module_and_board")
    if contract.get("status") != "product_scaffold_not_bonded_in_hello_chip":
        failures.append(
            "status must stay product_scaffold_not_bonded_in_hello_chip until pins are bonded"
        )

    reference = contract.get("reference_module", {})
    if reference.get("integration_file") != REFERENCE_MODULE:
        failures.append(f"reference_module.integration_file must be {REFERENCE_MODULE}")
    if reference.get("evidence_manifest") != EVIDENCE_MANIFEST:
        failures.append(f"reference_module.evidence_manifest must be {EVIDENCE_MANIFEST}")
    if reference.get("linux_wifi_driver") != "brcmfmac":
        failures.append("reference module must name brcmfmac as the Linux WiFi driver")
    if reference.get("commitment") != "reference_integration_slice_not_committed_bom":
        failures.append("reference module must remain a non-BOM reference slice")

    integration_state = contract.get("integration_state", {})
    for key, expected in REQUIRED_INTEGRATION_STATE.items():
        if integration_state.get(key) != expected:
            failures.append(f"integration_state.{key} must be {expected}")

    fail_closed = contract.get("fail_closed_policy", {})
    for key in ("linux_dts_nodes", "android_feature_claims", "firmware_artifacts", "board_release"):
        value = fail_closed.get(key, "")
        if "until" not in value and "blocked" not in value:
            failures.append(f"fail_closed_policy.{key} must describe a blocked/until condition")

    groups = contract.get("groups", {})
    for group, required_names in REQUIRED_GROUPS.items():
        signals = groups.get(group, {}).get("signals", [])
        names = {signal.get("name") for signal in signals}
        missing = sorted(required_names - names)
        if missing:
            failures.append(f"{group}: missing signals {', '.join(missing)}")

    all_names: list[str] = []
    for group, data in groups.items():
        if not isinstance(data, dict):
            failures.append(f"{group}: group entry must be a mapping")
            continue
        signals = data.get("signals", [])
        if not isinstance(signals, list):
            failures.append(f"{group}: signals must be a list")
            continue
        for signal in signals:
            if not isinstance(signal, dict):
                failures.append(f"{group}: signal entries must be mappings")
                continue
            name = signal.get("name", "<unnamed>")
            all_names.append(name)
            if signal.get("direction") not in ALLOWED_DIRECTIONS:
                failures.append(f"{name}: invalid direction {signal.get('direction')}")
            if signal.get("pull") not in ALLOWED_PULLS:
                failures.append(f"{name}: invalid pull {signal.get('pull')}")
            if signal.get("reset") not in ALLOWED_RESETS:
                failures.append(f"{name}: invalid reset {signal.get('reset')}")

    duplicates = sorted({name for name in all_names if all_names.count(name) > 1})
    if duplicates:
        failures.append("duplicate signal names: " + ", ".join(duplicates))

    module_path = root / REFERENCE_MODULE
    if not module_path.is_file():
        failures.append(f"{REFERENCE_MODULE} is missing")
    else:
        module = yaml.safe_load(module_path.read_text())
        if module.get("radio_claim") != "external_module_only":
            failures.append("reference module must keep radio_claim external_module_only")
        support = module.get("linux_support", {})
        if support.get("wifi_driver") != "brcmfmac":
            failures.append("reference module must use brcmfmac WiFi support")
        if support.get("bluetooth_driver") != "hci_uart_bcm":
            failures.append("reference module must use hci_uart_bcm Bluetooth support")
        if support.get("evidence_manifest") != EVIDENCE_MANIFEST:
            failures.append(f"reference module must point at {EVIDENCE_MANIFEST}")
        module_text = module_path.read_text()
        missing_reference_signals = sorted(
            name for name in REFERENCE_SIGNALS if name not in module_text
        )
        if missing_reference_signals:
            failures.append(
                "reference module is missing signals: " + ", ".join(missing_reference_signals)
            )

    evidence_path = root / EVIDENCE_MANIFEST
    if not evidence_path.is_file():
        failures.append(f"{EVIDENCE_MANIFEST} is missing")
    else:
        evidence = yaml.safe_load(evidence_path.read_text())
        if evidence.get("claim_policy") != "interface_only_no_wifi_implementation_claim":
            failures.append(
                "evidence manifest must keep interface_only_no_wifi_implementation_claim"
            )
        if evidence.get("status") != "blocked_no_host_controller_or_module":
            failures.append("evidence manifest must stay blocked_no_host_controller_or_module")
        release_blockers = evidence.get("product_release_blockers", [])
        if not isinstance(release_blockers, list):
            failures.append("evidence manifest product_release_blockers must be a list")
            release_blockers = []
        release_blockers_by_id = {
            item.get("id"): item for item in release_blockers if isinstance(item, dict)
        }
        missing_release_blockers = sorted(
            set(REQUIRED_RELEASE_BLOCKERS) - set(release_blockers_by_id)
        )
        if missing_release_blockers:
            failures.append(
                "evidence manifest missing product release blockers: "
                + ", ".join(missing_release_blockers)
            )
        for blocker_id, artifact_class in REQUIRED_RELEASE_BLOCKERS.items():
            blocker = release_blockers_by_id.get(blocker_id, {})
            if blocker.get("artifact_class") != artifact_class:
                failures.append(f"{blocker_id}: artifact_class must be {artifact_class}")
            if blocker.get("status") != "blocked":
                failures.append(
                    f"{blocker_id}: status must remain blocked until real evidence exists"
                )
            if "blocked" not in str(blocker.get("report", "")).lower():
                failures.append(f"{blocker_id}: report must state blocked")
            evidence_required = blocker.get("evidence_required", [])
            if not isinstance(evidence_required, list) or not evidence_required:
                failures.append(f"{blocker_id}: evidence_required must list release evidence")
        required_sections = {
            "host_controller",
            "board_package",
            "board_power_sequencing",
            "linux_bsp",
            "android_framework",
            "firmware",
            "regulatory",
        }
        required_evidence = evidence.get("required_evidence", {})
        missing_sections = sorted(required_sections - set(required_evidence))
        if missing_sections:
            failures.append("evidence manifest missing sections: " + ", ".join(missing_sections))
        for section in required_sections & set(required_evidence):
            section_data = required_evidence.get(section, {})
            if section_data.get("status") != "missing":
                failures.append(
                    f"evidence section {section} must remain missing until real evidence exists"
                )
            blockers = section_data.get("blockers", [])
            if not isinstance(blockers, list) or not blockers:
                failures.append(f"evidence section {section} must list blockers")
        evidence_text = evidence_path.read_text()
        for phrase in (
            "SDIO function enumeration",
            "brcmfmac",
            "hci_uart_bcm",
            "dumpsys wifi",
            "CTS/VTS",
            "sha256",
            "SAR",
            "FCC",
            "WIFI_EN",
            "WIFI_RST_N",
            "1.8 V IO bank",
        ):
            if phrase not in evidence_text:
                failures.append(f"evidence manifest must mention {phrase}")

    board_requirements = contract.get("board_requirements", [])
    required_phrases = ["RF", "antenna", "disabled", "Android", "regulatory"]
    joined = " ".join(board_requirements)
    for phrase in required_phrases:
        if phrase not in joined:
            failures.append(f"board_requirements must mention {phrase}")

    gates = contract.get("maturity_gates_before_product_claim", [])
    required_gate_terms = [
        "module",
        "SDIO host controller",
        "padframe",
        "driver",
        "Android",
        "evidence",
    ]
    gate_text = " ".join(gates)
    for term in required_gate_terms:
        if term not in gate_text:
            failures.append(f"maturity gates must mention {term}")

    doc = (root / "docs/arch/wifi.md").read_text()
    if "package/wifi-external-interface.yaml" not in doc:
        failures.append("docs/arch/wifi.md must reference the machine-readable WiFi contract")
    for phrase in ("not bonded", "not implemented", "maturity gates"):
        if phrase not in doc:
            failures.append(f"docs/arch/wifi.md must state {phrase}")
    for phrase in (
        "Murata Type 1DX",
        "brcmfmac",
        "hci_uart_bcm",
        "external",
        "package/wifi/evidence-gates.yaml",
    ):
        if phrase not in doc:
            failures.append(f"docs/arch/wifi.md must describe concrete slice term {phrase}")

    dts = (root / "sw/linux/dts/openphone-hello.dts").read_text()
    for phrase in (
        "mmc-pwrseq-simple",
        "brcm,bcm4329-fmac",
        "brcm,bcm43438-bt",
        'status = "disabled"',
    ):
        if phrase not in dts:
            failures.append(f"Linux DTS WiFi/Bluetooth stub must include {phrase}")

    linux_fragment = (root / "sw/buildroot/board/openphone/hello/linux.fragment").read_text()
    for phrase in ("CONFIG_BRCMFMAC", "CONFIG_BRCMFMAC_SDIO", "CONFIG_BT_HCIUART_BCM"):
        if phrase not in linux_fragment:
            failures.append(f"Buildroot Linux fragment must enable {phrase}")

    adapter_path = root / "board/fpga/package/wifi_external_module_adapter.yaml"
    if not adapter_path.is_file():
        failures.append("board/fpga/package/wifi_external_module_adapter.yaml is missing")
    else:
        adapter_text = adapter_path.read_text()
        for phrase in REFERENCE_SIGNALS:
            if phrase not in adapter_text:
                failures.append(f"FPGA WiFi adapter stub must mention {phrase}")
        if EVIDENCE_MANIFEST not in adapter_text:
            failures.append(f"FPGA WiFi adapter stub must reference {EVIDENCE_MANIFEST}")

    constraints = (root / "board/fpga/constraints/hello_demo_ulx3s.lpf").read_text()
    for phrase in ("WIFI_SDIO_CLK", "BT_UART_TX", "1.8 V", "Do not assign RF"):
        if phrase not in constraints:
            failures.append(f"FPGA constraints must reserve WiFi term {phrase}")

    if failures:
        print("WiFi interface contract check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("WiFi interface contract ok")
    evidence_path = root / EVIDENCE_MANIFEST
    if evidence_path.is_file():
        evidence = yaml.safe_load(evidence_path.read_text())
        release_blockers = evidence.get("product_release_blockers", [])
        if release_blockers:
            print("WiFi product/release blockers:")
            for blocker in release_blockers:
                print(f"  - {blocker['id']}: {blocker['report']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
