#!/usr/bin/env python3
from pathlib import Path
import sys

import yaml


REQUIRED_GROUPS = {
    "sdio": {"WIFI_SDIO_CLK", "WIFI_SDIO_CMD", "WIFI_SDIO_D0", "WIFI_SDIO_D1", "WIFI_SDIO_D2", "WIFI_SDIO_D3"},
    "control": {"WIFI_EN", "WIFI_RST_N"},
    "wake_irq": {"WIFI_HOST_WAKE", "WIFI_IRQ"},
    "bluetooth_uart": {"BT_UART_TX", "BT_UART_RX", "BT_UART_CTS_N", "BT_UART_RTS_N"},
}

REQUIRED_INTEGRATION_STATE = {
    "rtl_host_controller": "not_implemented",
    "padframe_bonding": "not_bonded_in_hello_chip",
    "firmware_driver": "not_implemented",
    "rf_certification": "module_and_board_responsibility",
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
        failures.append("status must stay product_scaffold_not_bonded_in_hello_chip until pins are bonded")

    integration_state = contract.get("integration_state", {})
    for key, expected in REQUIRED_INTEGRATION_STATE.items():
        if integration_state.get(key) != expected:
            failures.append(f"integration_state.{key} must be {expected}")

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

    board_requirements = contract.get("board_requirements", [])
    required_phrases = ["RF", "antenna", "disabled"]
    joined = " ".join(board_requirements)
    for phrase in required_phrases:
        if phrase not in joined:
            failures.append(f"board_requirements must mention {phrase}")

    gates = contract.get("maturity_gates_before_product_claim", [])
    required_gate_terms = ["module", "SDIO host controller", "padframe", "driver"]
    gate_text = " ".join(gates)
    for term in required_gate_terms:
        if term not in gate_text:
            failures.append(f"maturity gates must mention {term}")

    doc = (root / "arch/wifi.md").read_text()
    if "package/wifi-external-interface.yaml" not in doc:
        failures.append("arch/wifi.md must reference the machine-readable WiFi contract")
    for phrase in ("not bonded", "not implemented", "maturity gates"):
        if phrase not in doc:
            failures.append(f"arch/wifi.md must state {phrase}")

    if failures:
        print("WiFi interface contract check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("WiFi interface contract ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
