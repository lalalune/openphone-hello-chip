#!/usr/bin/env python3
from pathlib import Path
import re
import sys


def main() -> int:
    path = Path("verify/cocotb/results.xml")
    if not path.is_file():
        print("verify/cocotb/results.xml missing after cocotb run")
        return 1

    text = path.read_text(errors="ignore")
    failures = sum(int(value) for value in re.findall(r'failures="(\d+)"', text))
    errors = sum(int(value) for value in re.findall(r'errors="(\d+)"', text))
    failure_elements = len(re.findall(r"<failure\b", text))
    error_elements = len(re.findall(r"<error\b", text))
    testcases = len(re.findall(r"<testcase\b", text))

    if failures or errors or failure_elements or error_elements or not testcases:
        print(
            "cocotb XML indicates failure: "
            f"testcases={testcases} failures={failures + failure_elements} "
            f"errors={errors + error_elements}"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
