#!/usr/bin/env python3
from pathlib import Path
import re
import sys

import yaml


VECTOR_PIN_RE = re.compile(r"^(DBG_ADDR|DBG_WDATA|DBG_RDATA|GPIO)(\d+)$")


def parse_ports(path: Path) -> set[str]:
    text = path.read_text()
    module = re.search(r"module\s+hello_chip_top\s*\((.*?)\);", text, re.S)
    if not module:
        raise SystemExit("hello_chip_top module header not found")
    ports: set[str] = set()
    for raw in module.group(1).splitlines():
        raw = raw.split("//", 1)[0].strip().rstrip(",")
        if not raw:
            continue
        ports.add(raw.split()[-1].split("[", 1)[0])
    return ports


def logical_pin_name(name: str) -> str:
    vector = VECTOR_PIN_RE.match(name)
    return vector.group(1) if vector else name


def pin_order_patterns(path: Path) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile("^" + line.replace(".", r"\.").replace(r"\.*", ".*") + "$"))
    return patterns


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    contract = yaml.safe_load((root / "pd/padframe/hello_demo_padframe.yaml").read_text())
    pinout = yaml.safe_load((root / contract["package_pinout"]).read_text())
    pins = pinout.get("pins", [])
    allowed = contract["allowed"]
    failures: list[str] = []

    if len(pins) != contract["package_pins"]:
        failures.append(f"expected {contract['package_pins']} pins, found {len(pins)}")
    pin_numbers = sorted(pin["pin"] for pin in pins)
    if pin_numbers != list(range(1, contract["package_pins"] + 1)):
        failures.append("pin numbers must be contiguous from 1 through package_pins")

    seen_names: set[str] = set()
    logical_names: set[str] = set()
    power_counts = {"VDDIO": 0, "VSSIO": 0, "VDDCORE": 0, "VSSCORE": 0}

    for pin in pins:
        name = pin["name"]
        if name in seen_names:
            failures.append(f"duplicate pin name {name}")
        seen_names.add(name)
        logical_names.add(logical_pin_name(name))

        if pin["direction"] not in allowed["directions"]:
            failures.append(f"{name}: invalid direction {pin['direction']}")
        if pin["pad_type"] not in allowed["pad_types"]:
            failures.append(f"{name}: invalid pad_type {pin['pad_type']}")
        if pin["voltage_domain"] not in allowed["voltage_domains"]:
            failures.append(f"{name}: invalid voltage_domain {pin['voltage_domain']}")
        if pin["pull"] not in allowed["pulls"]:
            failures.append(f"{name}: invalid pull {pin['pull']}")

        if pin["direction"] == "power" and pin["pad_type"] != "power":
            failures.append(f"{name}: power direction requires power pad_type")
        if pin["direction"] == "ground" and pin["pad_type"] != "ground":
            failures.append(f"{name}: ground direction requires ground pad_type")
        if pin["direction"] == "nc" and (pin["pad_type"] != "no_connect" or pin["board_net"] != "NC"):
            failures.append(f"{name}: nc pins must use no_connect pad_type and NC board_net")

        for prefix in power_counts:
            if name.startswith(prefix):
                power_counts[prefix] += 1

    domains = contract["voltage_domains"]
    if power_counts["VDDIO"] < domains["io"]["min_power_pads"]:
        failures.append("insufficient VDDIO pads")
    if power_counts["VSSIO"] < domains["io"]["min_ground_pads"]:
        failures.append("insufficient VSSIO pads")
    if power_counts["VDDCORE"] < domains["core"]["min_power_pads"]:
        failures.append("insufficient VDDCORE pads")
    if power_counts["VSSCORE"] < domains["core"]["min_ground_pads"]:
        failures.append("insufficient VSSCORE pads")

    required_missing = sorted(set(contract["required_pins"]) - logical_names)
    if required_missing:
        failures.append("missing required padframe pins: " + ", ".join(required_missing))

    ports = parse_ports(root / contract["rtl_top"])
    missing_from_rtl = sorted((set(contract["required_pins"]) - {"VDDIO", "VSSIO", "VDDCORE", "VSSCORE"}) - ports)
    if missing_from_rtl:
        failures.append("padframe required pins missing from RTL: " + ", ".join(missing_from_rtl))

    patterns = pin_order_patterns(root / contract["pin_order"])
    missing_from_pin_order = sorted(port for port in ports if not any(pattern.match(port) for pattern in patterns))
    if missing_from_pin_order:
        failures.append("RTL ports missing from pd/pin_order.cfg: " + ", ".join(missing_from_pin_order))

    if failures:
        print("Padframe contract check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("padframe contract ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
