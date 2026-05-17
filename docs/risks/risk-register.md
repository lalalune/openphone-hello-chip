# Risk Register

The project is a fully open-source hardware Android phone research program.
The v0 prototype must keep the hardest closed-system risks outside the critical
path while still building real, testable artifacts.

| Risk | Severity | Likelihood | Failure mode | Mitigation |
|---|---|---|---|---|
| Snapdragon/Dimensity-class custom SoC scope | Critical | Very high | The project tries to build CPU, GPU, NPU, ISP, modem, LPDDR PHY, PMIC coupling, security, and BSP at once. | Keep v0 to `hello_soc`, open RTL expansion, and COTS board Android baseline. |
| Drop-in flagship pin compatibility | Critical | High | Proprietary package, PMIC, boot, RF, memory, and legal assumptions are copied or guessed. | Exclude pin compatibility; use architecture budgets only. |
| Advanced-node open silicon | Critical | Very high | Open PDK and open EDA cannot deliver phone-class PPA on modern nodes. | Use SKY130/GF180 only for demonstrators; use commercial silicon for phone baseline. |
| LTE/5G modem | Critical | Very high | Open modem stack cannot meet modern network, RF, certification, and carrier requirements. | Use certified external modem module; exclude integrated baseband. |
| LPDDR5X/LPDDR6 PHY | Critical | High | Mixed-signal PHY, training, SI/PI, and package co-design fail. | Use COTS SoC memory subsystem for product path; model only in open RTL path. |
| GPU and Android graphics | Critical | High | No performant Vulkan/GLES stack, HWC, gralloc, sync, or CTS behavior. | Framebuffer first; conformance before performance; no flagship GPU claim in v0. |
| Camera ISP | Critical | High | Sensor tuning, 3A, HDR, denoise, HAL3, and calibration are missing. | UVC/simple camera only; exclude computational photography. |
| Android compatibility | Critical | High | AOSP boots but CTS/VTS/HAL/Treble fail. | Track AOSP boot separately from compatibility; run subsets early. |
| Power and thermal | High | High | Benchmarks pass briefly but device throttles or drains battery. | Require sustained loops and external power measurement for product claims. |
| Verification burden | Critical | Very high | RTL bug survives to tapeout or corrupts memory/security state. | Formal, cocotb, Verilator, FireSim, Linux stress, and release gates. |
| Floating toolchain inputs | High | High | A later Docker apt, Nix, OpenLane2, Chipyard, or Python package update changes results or breaks a reproduced run. | Require `.venv`, tool version reports, lockfiles/digests/SHAs before release evidence. |
| Local fork drift | High | Medium | A private OpenLane/Chipyard/PDK/AOSP patch becomes the only working path and cannot be reviewed or upstreamed. | Fork only for named release blockers; record upstream base SHA, patch branch, and retirement plan. |
| Scaffold check mistaken for proof | High | High | Missing OpenLane/Renode/AOSP/FPGA tools are hidden behind docs-only checks and treated as implementation evidence. | Every absent heavy tool must map to an explicit blocked gate and required unblock artifact. |

## v0 Non-Goals

- no integrated cellular baseband
- no carrier certification
- no GMS or Play certification
- no Widevine L1 or HDCP
- no flagship GPU
- no production camera ISP
- no custom LPDDR PHY
- no advanced-node tapeout
- no copied competitor pinout or package compatibility
