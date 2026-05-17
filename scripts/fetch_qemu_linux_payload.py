#!/usr/bin/env python3
"""Fetch a real riscv64 QEMU Linux payload from Debian netboot artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = (
    "https://deb.debian.org/debian/dists/stable/main/installer-riscv64/current/images"
)
PAYLOADS = {
    "linux": "netboot/debian-installer/riscv64/linux",
    "initrd.gz": "netboot/debian-installer/riscv64/initrd.gz",
}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    if shutil.which("curl"):
        subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--retry",
                "3",
                "--connect-timeout",
                "15",
                "--max-time",
                "300",
                "--output",
                str(tmp),
                url,
            ],
            check=True,
        )
        tmp.replace(destination)
        return
    with urllib.request.urlopen(url, timeout=60) as response:
        tmp.write_bytes(response.read())
    tmp.replace(destination)


def parse_sha256s(text: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) != 2:
            continue
        digest, rel = parts
        hashes[rel.removeprefix("./")] = digest
    return hashes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--output-dir",
        default="build/qemu/linux_payload/debian-installer-riscv64",
        help="Directory for downloaded linux/initrd.gz artifacts.",
    )
    parser.add_argument("--force", action="store_true", help="Download even when files exist.")
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    out_dir = ROOT / args.output_dir
    sha_url = f"{base_url}/SHA256SUMS"
    sha_file = out_dir / "SHA256SUMS"
    print(f"fetch {sha_url}", flush=True)
    fetch(sha_url, sha_file)
    expected = parse_sha256s(sha_file.read_text(encoding="utf-8", errors="ignore"))

    manifest: dict[str, object] = {
        "schema": "openphone.qemu_linux_payload.v1",
        "claim_boundary": "qemu_virt_debian_netboot_payload_only",
        "created_utc": utc_now(),
        "base_url": base_url,
        "sha256s_url": sha_url,
        "payloads": {},
    }
    payloads: dict[str, object] = {}
    for name, rel_url in PAYLOADS.items():
        expected_hash = expected.get(rel_url)
        if not expected_hash:
            print(f"error: SHA256SUMS lacks {rel_url}", file=sys.stderr)
            return 1
        destination = out_dir / name
        url = f"{base_url}/{rel_url}"
        if args.force or not destination.is_file():
            print(f"fetch {url}", flush=True)
            fetch(url, destination)
        actual_hash = sha256_path(destination)
        if actual_hash != expected_hash:
            print(
                f"error: sha256 mismatch for {destination}: expected {expected_hash}, got {actual_hash}",
                file=sys.stderr,
            )
            return 1
        payloads[name] = {
            "path": str(destination.relative_to(ROOT)),
            "url": url,
            "sha256": actual_hash,
            "bytes": destination.stat().st_size,
        }
        print(f"verified {destination.relative_to(ROOT)} sha256={actual_hash}", flush=True)

    manifest["payloads"] = payloads
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {manifest_path.relative_to(ROOT)}", flush=True)
    print("next: scripts/run_qemu.sh --check-os", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
