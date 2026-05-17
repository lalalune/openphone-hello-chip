# U-Boot port scaffold

U-Boot starts after the Chipyard/Rocket software reference can boot OpenSBI and
expose RAM, UART, timer, and interrupt devices tied to
`sw/platform/hello_platform_contract.json`.

Repo-local command:

```sh
make software-bsp-check
python3 sw/check_bsp_scaffolds.py boot
```

Expected output:

```text
buildroot BSP check passed.
linux BSP check passed.
aosp BSP check passed.
boot: scaffold audit
  local command: make software-bsp-check
  expected output: buildroot BSP check passed.; linux BSP check passed.; aosp BSP check passed.
  dependency blocker: CPU-capable SoC integration with RAM, UART, timer, interrupt controller, OpenSBI handoff
  status: clear
```

Dependency blocker: a real U-Boot port requires a working OpenSBI handoff,
DRAM map, UART console, timer, interrupt controller, boot media, and device tree
from the CPU-capable target. Until then this directory is documentation-only and
must not be treated as boot evidence.
