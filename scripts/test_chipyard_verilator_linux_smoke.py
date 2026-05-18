#!/usr/bin/env python3
"""Unit tests for Chipyard Verilator Linux smoke path handling."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_chipyard_verilator_linux_smoke as smoke  # noqa: E402


def test_detects_container_paths_when_host_is_not_container_mount() -> None:
    text = "VM_PREFIX = /work/external/oss-cad-suite-linux-x64/bin\n"
    roots = smoke.detect_stale_absolute_roots(text, Path("/Users/example/npu_experiment"), False)
    if roots != ["/work/"]:
        raise AssertionError(f"expected /work/ stale root, got {roots}")


def test_allows_container_paths_when_running_inside_container_mount() -> None:
    text = "VM_PREFIX = /work/external/oss-cad-suite-linux-x64/bin\n"
    roots = smoke.detect_stale_absolute_roots(text, Path("/work"), False)
    if roots:
        raise AssertionError(f"expected no stale roots under /work host root, got {roots}")


def test_allow_env_semantics_suppress_container_path_block() -> None:
    text = "VM_PREFIX = /work/external/oss-cad-suite-linux-x64/bin\n"
    roots = smoke.detect_stale_absolute_roots(text, Path("/Users/example/npu_experiment"), True)
    if roots:
        raise AssertionError(f"expected allow flag to suppress stale roots, got {roots}")


def test_non_container_absolute_path_is_not_flagged_by_this_gate() -> None:
    text = "VM_PREFIX = /opt/conda/bin\n"
    roots = smoke.detect_stale_absolute_roots(text, Path("/Users/example/npu_experiment"), False)
    if roots:
        raise AssertionError(f"unexpected stale roots for unrelated path: {roots}")


def main() -> int:
    tests = (
        test_detects_container_paths_when_host_is_not_container_mount,
        test_allows_container_paths_when_running_inside_container_mount,
        test_allow_env_semantics_suppress_container_path_block,
        test_non_container_absolute_path_is_not_flagged_by_this_gate,
    )
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
