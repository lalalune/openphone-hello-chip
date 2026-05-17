#!/usr/bin/env python3
import json
import re
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path


def parse_stats(text: str) -> dict[str, int]:
    failures = sum(int(value) for value in re.findall(r'failures="(\d+)"', text))
    errors = sum(int(value) for value in re.findall(r'errors="(\d+)"', text))
    failure_elements = len(re.findall(r"<failure\b", text))
    error_elements = len(re.findall(r"<error\b", text))
    testcases = len(re.findall(r"<testcase\b", text))
    return {
        "testcases": testcases,
        "failures": failures + failure_elements,
        "errors": errors + error_elements,
    }


def archive_result(
    path: Path,
    archive_name: str,
    manifest_path: Path,
    stats: dict[str, int],
    top: str,
    module: str,
) -> None:
    report_dir = manifest_path.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    xml_name = f"{archive_name}.xml"
    xml_path = report_dir / xml_name
    shutil.copy2(path, xml_path)

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"schema": "openphone.cocotb_manifest.v1", "targets": {}}
    if not isinstance(manifest, dict):
        manifest = {"schema": "openphone.cocotb_manifest.v1", "targets": {}}
    targets = manifest.setdefault("targets", {})
    if not isinstance(targets, dict):
        manifest["targets"] = targets = {}
    targets[archive_name] = {
        "top": top,
        "module": module,
        "result_xml": str(xml_path),
        "stats": stats,
    }
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    tmp.replace(manifest_path)


def main() -> int:
    parser = ArgumentParser(description="Validate and optionally archive cocotb XML results.")
    parser.add_argument("--result-xml", default="verify/cocotb/results.xml")
    parser.add_argument("--archive-name", help="archive passing XML under build/reports/cocotb")
    parser.add_argument("--top", default="")
    parser.add_argument("--module", default="")
    parser.add_argument("--manifest", default="build/reports/cocotb/manifest.json")
    args = parser.parse_args()

    path = Path(args.result_xml)
    if not path.is_file():
        print(f"{path} missing after cocotb run")
        return 1

    text = path.read_text(errors="ignore")
    stats = parse_stats(text)

    if stats["failures"] or stats["errors"] or not stats["testcases"]:
        print(
            "cocotb XML indicates failure: "
            f"testcases={stats['testcases']} failures={stats['failures']} "
            f"errors={stats['errors']}"
        )
        return 1

    if args.archive_name:
        archive_result(path, args.archive_name, Path(args.manifest), stats, args.top, args.module)

    return 0


if __name__ == "__main__":
    sys.exit(main())
