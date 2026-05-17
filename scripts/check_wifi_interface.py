#!/usr/bin/env python3
import hashlib
import re
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
EVIDENCE_SCHEMA = "openphone.wifi_bluetooth_evidence_gates.v1"
CAPTURE_TEMPLATE = "package/wifi/release-evidence-template.yaml"
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
REQUIRED_CAPTURE_TEMPLATE_FIELDS = {
    "template",
    "status",
    "artifact_record_required_fields",
    "metadata_required_fields",
    "acceptance_required_fields",
    "forbidden_claims",
}
REQUIRED_EVIDENCE_RECORD_FIELDS = {
    "blocker_id",
    "artifact_name",
    "artifact_class",
    "source_path",
    "captured_at",
    "captured_by",
    "board_or_platform_revision",
    "selected_module",
    "sha256",
    "acceptance_status",
    "acceptance_criteria",
    "raw_log_or_capture",
    "linked_release_blocker",
    "supersedes_scaffold_claim",
    "reviewer",
}
ACCEPTED_RELEASE_STATUSES = {"accepted", "approved", "pass"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_RELEASE_PATH_PARTS = {"placeholder", "template", "scaffold", "skeleton"}
FORBIDDEN_RELEASE_TEXT_MARKERS = (
    "template_not_release_evidence",
    "non_release_placeholder",
    "release use: `prohibited`",
    "release_use: prohibited",
    "placeholder-only",
    "interface_only_no_wifi_implementation_claim",
    "not release evidence",
)


def as_nonempty_string_list(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value
    return []


def validate_repo_relative_path(field: str, value: object, failures: list[str]) -> None:
    if not isinstance(value, str) or not value:
        failures.append(f"{field} must be a non-empty repo-relative path")
        return
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        failures.append(f"{field} must be a repo-relative path: {value}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_matches_globs(path: str, globs: list[str]) -> bool:
    candidate = Path(path)
    return any(candidate.match(pattern) for pattern in globs)


def validate_capture_template(root: Path, failures: list[str]) -> None:
    template_path = root / CAPTURE_TEMPLATE
    if not template_path.is_file():
        failures.append(f"{CAPTURE_TEMPLATE} is missing")
        return
    template = yaml.safe_load(template_path.read_text())
    if not isinstance(template, dict):
        failures.append(f"{CAPTURE_TEMPLATE} must be a YAML mapping")
        return
    missing = sorted(REQUIRED_CAPTURE_TEMPLATE_FIELDS - set(template))
    if missing:
        failures.append(f"{CAPTURE_TEMPLATE} missing fields: " + ", ".join(missing))
    if template.get("status") != "template_not_release_evidence":
        failures.append(f"{CAPTURE_TEMPLATE} status must be template_not_release_evidence")
    for field in (
        "artifact_record_required_fields",
        "metadata_required_fields",
        "acceptance_required_fields",
        "forbidden_claims",
    ):
        if not as_nonempty_string_list(template.get(field)):
            failures.append(f"{CAPTURE_TEMPLATE}.{field} must be a non-empty string list")


def validate_evidence_record_requirements(evidence: dict, failures: list[str]) -> None:
    requirements = evidence.get("evidence_record_requirements")
    if not isinstance(requirements, dict):
        failures.append("evidence manifest must list evidence_record_requirements")
        return
    fields = set(as_nonempty_string_list(requirements.get("required_fields")))
    missing_fields = sorted(REQUIRED_EVIDENCE_RECORD_FIELDS - fields)
    if missing_fields:
        failures.append(
            "evidence_record_requirements.required_fields missing: " + ", ".join(missing_fields)
        )
    accepted = set(as_nonempty_string_list(requirements.get("accepted_release_statuses")))
    if not ACCEPTED_RELEASE_STATUSES.issubset(accepted):
        failures.append(
            "evidence_record_requirements.accepted_release_statuses must include: "
            + ", ".join(sorted(ACCEPTED_RELEASE_STATUSES))
        )
    if requirements.get("linked_release_gate") != "wifi_bluetooth_product_claim":
        failures.append(
            "evidence_record_requirements.linked_release_gate must be wifi_bluetooth_product_claim"
        )
    if requirements.get("supersedes_scaffold_claim_required") is not True:
        failures.append(
            "evidence_record_requirements.supersedes_scaffold_claim_required must be true"
        )


def validate_evidence_records(
    root: Path,
    field: str,
    records: object,
    capture_globs: list[str],
    allowed_blockers: set[str],
    failures: list[str],
) -> None:
    if records is None:
        return
    if not isinstance(records, list):
        failures.append(f"{field}.evidence_records must be a list")
        return
    if not records:
        failures.append(f"{field}.evidence_records must be non-empty when present")
        return
    for index, record in enumerate(records):
        record_field = f"{field}.evidence_records[{index}]"
        if not isinstance(record, dict):
            failures.append(f"{record_field} must be a mapping")
            continue
        missing = sorted(REQUIRED_EVIDENCE_RECORD_FIELDS - set(record))
        if missing:
            failures.append(f"{record_field} missing required fields: " + ", ".join(missing))

        blocker_id = record.get("blocker_id")
        if blocker_id not in allowed_blockers:
            failures.append(f"{record_field}.blocker_id must be one of known WiFi blockers")
        if record.get("linked_release_blocker") != blocker_id:
            failures.append(f"{record_field}.linked_release_blocker must match blocker_id")
        if record.get("supersedes_scaffold_claim") is not True:
            failures.append(f"{record_field}.supersedes_scaffold_claim must be true")
        if record.get("acceptance_status") not in ACCEPTED_RELEASE_STATUSES:
            failures.append(
                f"{record_field}.acceptance_status must be one of "
                + ", ".join(sorted(ACCEPTED_RELEASE_STATUSES))
            )

        source_path = record.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            failures.append(f"{record_field}.source_path must be a repo-relative file path")
            continue
        validate_repo_relative_path(f"{record_field}.source_path", source_path, failures)
        lower_parts = {part.lower() for part in Path(source_path).parts}
        forbidden_parts = sorted(FORBIDDEN_RELEASE_PATH_PARTS & lower_parts)
        if forbidden_parts:
            failures.append(
                f"{record_field}.source_path contains forbidden part(s): "
                + ", ".join(forbidden_parts)
            )
        if source_path == CAPTURE_TEMPLATE:
            failures.append(f"{record_field}.source_path must not be the capture template")
        if capture_globs and not path_matches_globs(source_path, capture_globs):
            failures.append(f"{record_field}.source_path must match this evidence section globs")
        path = root / source_path
        if not path.is_file():
            failures.append(f"{record_field}.source_path file is missing: {source_path}")
            continue
        text = path.read_text(errors="ignore").lower()
        matched_markers = [marker for marker in FORBIDDEN_RELEASE_TEXT_MARKERS if marker in text]
        if matched_markers:
            failures.append(
                f"{record_field}.source_path contains non-release marker(s): "
                + ", ".join(matched_markers)
            )
        sha256 = record.get("sha256")
        if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
            failures.append(f"{record_field}.sha256 must be lowercase sha256")
        elif file_sha256(path) != sha256:
            failures.append(f"{record_field}.sha256 does not match file content")


REQUIRED_POWER_SEQUENCE_TERMS = (
    "WIFI_EN",
    "WIFI_RST_N",
    "VBAT",
    "VDDIO_1V8",
    "1.8V VDDIO",
    "SDIO clock",
    "UART RTS/CTS",
    "WIFI_HOST_WAKE",
    "WIFI_IRQ",
)


def signal_names(group: dict) -> set[str]:
    names: set[str] = set()
    for signal in group.get("signals", []):
        if isinstance(signal, dict):
            name = signal.get("name")
            if isinstance(name, str):
                names.add(name)
    return names


def module_contract_names(interface: dict) -> set[str]:
    contracts: set[str] = set()
    for signal in interface.get("signals", []):
        if isinstance(signal, dict):
            contract = signal.get("contract")
            if isinstance(contract, str):
                contracts.add(contract)
    return contracts


def validate_power_sequence(label: str, sequence: dict, failures: list[str]) -> None:
    if sequence.get("status") not in {"required_not_implemented", "blocked_until_board_revision"}:
        failures.append(f"{label}.status must stay blocked/required-not-implemented")
    controls = sequence.get("default_controls", {})
    for control in ("WIFI_EN", "WIFI_RST_N"):
        if controls.get(control) != "low":
            failures.append(f"{label}.default_controls.{control} must be low")
    rails = sequence.get("rails", [])
    rail_text = " ".join(str(rail) for rail in rails)
    for rail in ("VBAT", "VDDIO_1V8"):
        if rail not in rail_text:
            failures.append(f"{label}.rails must include {rail}")
    steps = sequence.get("ordered_steps", [])
    if not isinstance(steps, list) or len(steps) < 5:
        failures.append(f"{label}.ordered_steps must list the sequencing evidence contract")
        steps = []
    steps_text = " ".join(str(step) for step in steps)
    for term in REQUIRED_POWER_SEQUENCE_TERMS:
        if term not in steps_text:
            failures.append(f"{label}.ordered_steps must mention {term}")


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

    validate_power_sequence(
        "power_sequence_contract",
        contract.get("power_sequence_contract", {}),
        failures,
    )

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

    contract_sdio = signal_names(groups.get("sdio", {}))
    contract_control_wake = signal_names(groups.get("control", {})) | signal_names(
        groups.get("wake_irq", {})
    )
    contract_bluetooth_uart = signal_names(groups.get("bluetooth_uart", {}))

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
        host_interfaces = module.get("host_interfaces", {})
        if module_contract_names(host_interfaces.get("sdio_wifi", {})) != contract_sdio:
            failures.append("reference module SDIO contracts must match package SDIO signals")
        if module_contract_names(host_interfaces.get("control", {})) != contract_control_wake:
            failures.append(
                "reference module control contracts must match package control/wake signals"
            )
        if (
            module_contract_names(host_interfaces.get("bluetooth_uart", {}))
            != contract_bluetooth_uart
        ):
            failures.append(
                "reference module Bluetooth UART contracts must match package UART signals"
            )
        if host_interfaces.get("sdio_wifi", {}).get("io_voltage") != contract.get("io_voltage"):
            failures.append("reference module SDIO io_voltage must match package WiFi io_voltage")
        validate_power_sequence(
            "reference_module.power_sequence",
            module.get("power_sequence", {}),
            failures,
        )
        contract_steps = contract.get("power_sequence_contract", {}).get("ordered_steps", [])
        module_steps = module.get("power_sequence", {}).get("ordered_steps", [])
        if contract_steps != module_steps:
            failures.append(
                "reference module power_sequence ordered_steps must match package contract"
            )

    evidence_path = root / EVIDENCE_MANIFEST
    if not evidence_path.is_file():
        failures.append(f"{EVIDENCE_MANIFEST} is missing")
    else:
        evidence = yaml.safe_load(evidence_path.read_text())
        if evidence.get("schema") != EVIDENCE_SCHEMA:
            failures.append(f"evidence manifest schema must be {EVIDENCE_SCHEMA}")
        if evidence.get("capture_template") != CAPTURE_TEMPLATE:
            failures.append(f"evidence manifest capture_template must be {CAPTURE_TEMPLATE}")
        validate_repo_relative_path(
            "evidence manifest capture_template", evidence.get("capture_template"), failures
        )
        if evidence.get("claim_policy") != "interface_only_no_wifi_implementation_claim":
            failures.append(
                "evidence manifest must keep interface_only_no_wifi_implementation_claim"
            )
        if evidence.get("status") != "blocked_no_host_controller_or_module":
            failures.append("evidence manifest must stay blocked_no_host_controller_or_module")
        validate_evidence_record_requirements(evidence, failures)
        release_blockers = evidence.get("product_release_blockers", [])
        if not isinstance(release_blockers, list):
            failures.append("evidence manifest product_release_blockers must be a list")
            release_blockers = []
        release_blockers_by_id: dict[str, dict] = {}
        blocker_counts: dict[str, int] = {}
        for item in release_blockers:
            if not isinstance(item, dict):
                continue
            blocker_id = item.get("id")
            if isinstance(blocker_id, str):
                release_blockers_by_id[blocker_id] = item
                blocker_counts[blocker_id] = blocker_counts.get(blocker_id, 0) + 1
        duplicate_release_blockers = sorted(
            blocker_id for blocker_id, count in blocker_counts.items() if count > 1
        )
        if duplicate_release_blockers:
            failures.append(
                "evidence manifest duplicate product release blockers: "
                + ", ".join(str(item) for item in duplicate_release_blockers)
            )
        unknown_release_blockers = sorted(
            set(release_blockers_by_id) - set(REQUIRED_RELEASE_BLOCKERS)
        )
        if unknown_release_blockers:
            failures.append(
                "evidence manifest unknown product release blockers: "
                + ", ".join(str(item) for item in unknown_release_blockers)
            )
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
            capture_fields = blocker.get("capture_fields", [])
            if not as_nonempty_string_list(capture_fields):
                failures.append(f"{blocker_id}: capture_fields must list evidence record fields")
            validate_evidence_records(
                root,
                f"product_release_blockers.{blocker_id}",
                blocker.get("evidence_records"),
                [],
                set(REQUIRED_RELEASE_BLOCKERS),
                failures,
            )
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
            capture_globs = section_data.get("capture_globs", [])
            if not as_nonempty_string_list(capture_globs):
                failures.append(f"evidence section {section} must list capture_globs")
            for pattern in capture_globs:
                validate_repo_relative_path(
                    f"evidence section {section}.capture_globs", pattern, failures
                )
            validate_evidence_records(
                root,
                f"required_evidence.{section}",
                section_data.get("evidence_records"),
                capture_globs if isinstance(capture_globs, list) else [],
                set(REQUIRED_RELEASE_BLOCKERS),
                failures,
            )
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
    validate_capture_template(root, failures)

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
        adapter = yaml.safe_load(adapter_path.read_text())
        adapter_text = adapter_path.read_text()
        for phrase in REFERENCE_SIGNALS:
            if phrase not in adapter_text:
                failures.append(f"FPGA WiFi adapter stub must mention {phrase}")
        if EVIDENCE_MANIFEST not in adapter_text:
            failures.append(f"FPGA WiFi adapter stub must reference {EVIDENCE_MANIFEST}")
        adapter_banks = adapter.get("io_bank_requirements", {})
        if set(adapter_banks.get("sdio_wifi", {}).get("signals", [])) != contract_sdio:
            failures.append("FPGA WiFi adapter SDIO signals must match package SDIO signals")
        if (
            set(adapter_banks.get("control_and_wake", {}).get("signals", []))
            != contract_control_wake
        ):
            failures.append(
                "FPGA WiFi adapter control/wake signals must match package control/wake signals"
            )
        if (
            set(adapter_banks.get("bluetooth_uart", {}).get("signals", []))
            != contract_bluetooth_uart
        ):
            failures.append(
                "FPGA WiFi adapter Bluetooth UART signals must match package UART signals"
            )
        for bank_name in ("sdio_wifi", "control_and_wake", "bluetooth_uart"):
            if adapter_banks.get(bank_name, {}).get("voltage") != contract.get("io_voltage"):
                failures.append(
                    f"FPGA WiFi adapter {bank_name} voltage must match package WiFi io_voltage"
                )
        validate_power_sequence(
            "fpga_adapter.power_sequence_requirements",
            adapter.get("power_sequence_requirements", {}),
            failures,
        )
        adapter_steps = adapter.get("power_sequence_requirements", {}).get("ordered_steps", [])
        contract_steps = contract.get("power_sequence_contract", {}).get("ordered_steps", [])
        if adapter_steps != contract_steps:
            failures.append(
                "FPGA WiFi adapter power_sequence ordered_steps must match package contract"
            )

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
