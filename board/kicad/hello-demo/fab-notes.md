# Hello demo board — fabrication and design specification

This document is the authoritative design specification for the hello-demo evaluation board.
It drives the KiCad project, the DFM review, the assembly notes, and the first-article
bring-up procedure.

This document does not constitute fabrication release. Fabrication is blocked until:
- Package is not a placeholder (package vendor drawing must be archived).
- Footprint is derived from vendor package data.
- KiCad ERC and DRC pass with 0 errors.
- Gerber export and DFM review are complete.
- SI/PI and PDN evidence is archived.

See `docs/manufacturing/physical-closure-work-order.yaml` for all acceptance criteria.

---

## Board Specification

| Parameter | Value |
|---|---|
| Form factor | 100mm x 80mm (evaluation board) |
| Layer count | 4 |
| L1 | Signal (top/component side) |
| L2 | GND reference plane (solid copper pour) |
| L3 | PWR plane (split: VDDCORE region + VDDIO_3V3 region + VDDIO_1V8 region) |
| L4 | Signal (bottom side) |
| Core material | FR4, Tg = 170°C (mid-Tg FR4 for reflow robustness) |
| L1-L2 dielectric | 0.2mm prepreg (e.g., Isola 370HR or equivalent) |
| L2-L3 core | 0.6mm FR4 core |
| L3-L4 dielectric | 0.2mm prepreg |
| Total board thickness | ~1.6mm (including copper layers) |
| Copper weight, outer layers (L1, L4) | 1 oz (35 µm) |
| Copper weight, inner layers (L2, L3) | 0.5 oz (17.5 µm) |
| Min trace width | 0.127mm (5 mil) |
| Min trace spacing | 0.127mm (5 mil) |
| Min via drill | 0.3mm |
| Min via annular ring | 0.15mm (via pad = 0.6mm) |
| Controlled impedance | 50Ω ±10% single-ended on L1 and L4 (trace width ~0.36mm over L2 GND at 0.2mm dielectric) |
| Surface finish | ENIG (Electroless Nickel Immersion Gold), 2-6µin Au / 120-240µin Ni |
| Solder mask | LPI (Liquid Photoimageable), green, both sides |
| Silkscreen | White LPI, both sides |
| IPC class | Class 2 (general electronic products) |
| Min hole size (drill) | 0.3mm (laser via) or 0.8mm (mechanical drill for through-hole) |
| Panel | Single board, no panelization for prototype run |

---

## Power Design

### Supply rails

| Rail | Regulator | Target voltage | Max current | Input | Notes |
|---|---|---|---|---|---|
| VDDCORE | TPS62150RGTR | 0.8V | 3A | 5V USB-C or 12V barrel → buck pre-reg | Adjustable output; set with R_top/R_bot resistor divider; Vout = 0.8*(1 + R_top/R_bot) |
| VDDIO_3V3 | TLV74033PDBVR | 3.3V | 500mA | 5V USB-C | Fixed-output LDO; SOT-23-5 package |
| VDDIO_1V8 | TLV74018PDBVR | 1.8V | 500mA | 3.3V (from TLV74033) | Fixed-output LDO in LDO chain; SOT-23-5 package |

### TPS62150 configuration (VDDCORE)

- Input voltage: 4.5V–17V (supports USB-C 5V and 12V barrel jack input directly)
- Output voltage setpoint: 0.8V; feedback resistors R_top = 100kΩ, R_bot = 549kΩ (compute from
  Vout = 0.8 * (1 + R_top/R_bot); confirm against TPS62150 datasheet Eq. 2)
- Switching frequency: 2.25 MHz (COT mode, set by mode pin; reduces output inductor size)
- Output inductor: 1µH, ISAT >= 3A, DCR <= 50mΩ (e.g., Bourns SRR4018-1R0Y or Wurth 744043100)
- Output capacitor: 2x 47µF 6.3V X5R 0805 ceramic (main output) + 10µF 10V X5R 0603 (at IC output)
- Input capacitor: 10µF 25V X7R 0805 ceramic (at VIN pin), 100nF 25V X7R 0402 (bypass)
- Enable pin: pulled to VBUS via 100kΩ; no sequencing needed for evaluation board
- Power good output: pulled up via 100kΩ to 3.3V; routed to MCU/debug GPIO for monitoring

### TLV74033 configuration (VDDIO_3V3)

- Input: VBUS (5V from USB-C or regulated 5V from barrel jack path)
- Output: 3.3V fixed
- Input capacitor: 1µF 10V X5R 0402 (per datasheet minimum)
- Output capacitor: 1µF 10V X5R 0402 (per datasheet minimum) + 10µF 10V X5R 0603 bulk
- Ferrite bead on output: Murata BLM21PG221SN1L (220Ω at 100 MHz), rated 1A; placed between
  LDO output and VDDIO_3V3 power plane; bypass the bead with 1µF X5R 0402 on the chip side

### TLV74018 configuration (VDDIO_1V8)

- Input: VDDIO_3V3 (LDO chain; input to TLV74018 is 3.3V)
- Output: 1.8V fixed
- Input capacitor: 1µF 10V X5R 0402
- Output capacitor: 1µF 10V X5R 0402 + 10µF 6.3V X5R 0603 bulk
- Ferrite bead on output: Murata BLM21PG221SN1L (same as 3.3V bead), rated 1A; placed between
  LDO output and VDDIO_1V8 power plane

### Input supply

- USB-C connector: USB4135-GF-A (GCT) USB Type-C receptacle, 2-position power-only (VBUS + GND)
- USB-C operates as a power sink only (no data); VBUS from USB-C host is 5V typical (no PD negotiation)
- Barrel jack: CUI PJ-002A (5.5mm OD / 2.1mm ID), accepts 7V–17V input
- Input protection: PRTR5V0U2X TVS diode (Nexperia) on USB-C VBUS; reverse polarity protection MOSFET (e.g., IRLML0030TRPBF, P-channel) on barrel jack input
- Input selection: Schottky ORing diodes (PMEG4002EL) from each input to a common 5V rail feeding the regulators; barrel jack input passes through a step-down pre-regulator (TPS62150 or VBUS ORed) to 5V when vin > 5.5V

### Bulk capacitance

- 470µF 6.3V electrolytic (Panasonic EEE-FK0J471P or equivalent) on each of VDDCORE, VDDIO_3V3, and VDDIO_1V8 rails (placed at the regulator output, before the ferrite bead)
- 100nF X7R 0402 + 10nF X7R 0402 decoupling capacitor pair on each VDD pin of the SoC package;
  100nF placed within 0.5mm of the package pad, 10nF placed within 1.5mm; connected with short,
  wide (>=0.3mm) traces directly to the VDD pad and the nearest via to the L2 GND or L3 PWR plane

---

## Oscillator

| Parameter | Value |
|---|---|
| Part number | SiT8924B-11-18E-24.000 |
| Frequency | 24.000 MHz |
| Frequency stability | ±25 ppm (±10 ppm option available as SiT8924B-11-18E-24.000 with -E suffix) |
| Supply voltage | 1.8V (1.71V–1.89V operating range) |
| Output type | CMOS, single-ended |
| Package | 3.2mm x 2.5mm, 4-pad SMD |
| Drive strength | 8 mA typical |
| Output load | 15 pF max |
| Enable/OE pin | Active-high; pulled to VDDIO_1V8 via 100kΩ for always-on operation |
| CLK output net | CLK_24M; 50Ω controlled impedance trace to SoC CLK_IN pin |
| Supply decoupling | 100nF X7R 0402 from VDD to GND, placed within 0.5mm of oscillator VDD pad |

Crystal loading note: The SiT8924B is a MEMS oscillator (integrated resonator); it does not
require external load capacitors. If a crystal-based circuit (e.g., ABM8G-24.000MHZ-18-D2Y-T3)
is substituted, add 18 pF NP0 0402 caps on XI and XO pads to GND, and a series 0Ω/DNP resistor
on XO for drive-strength tuning. Drive strength characterization is required before committing
crystal component type; the MEMS oscillator is the preferred option to avoid this dependency.

---

## Reset Circuit

| Parameter | Value |
|---|---|
| Supervisor part | MAX823LEUR+T (Maxim/Analog Devices) |
| Package | SOT-23-5 |
| Monitored rail | VDDIO_3V3 (3.3V supply) |
| Reset threshold | 3.08V (falling), 3.08V + hysteresis (rising) |
| Reset output polarity | Active-low, push-pull |
| Reset output net | nRST (connects to SoC RST_N and debug connector pin nSRST) |
| Minimum reset assert time | 140ms (internal timer from power-on or VDDIO_3V3 dip) |
| Manual reset button | Tactile switch (C&K PTS645 series, 6mm x 6mm SMD) between nRST and GND |
| Manual reset debounce | 100nF NP0 0402 from nRST to GND (in addition to MAX823L internal debounce; results in additional ~50µs RC constant, negligible against 140ms supervisor hold time) |
| Reset LED | Red LED (Wurth 150060RS55040, 0603) with 1kΩ series resistor from 3.3V to nRST; LED lights when nRST is deasserted (board out of reset). Pull the LED cathode to nRST via a small-signal NPN (MMBT2222A, SOT-23) with base resistor 10kΩ from nRST, so the LED does not load the reset line. |
| Power-on sequencing | VDDIO_3V3 monitored; nRST holds SoC in reset until 3.3V is stable; VDDCORE and VDDIO_1V8 are expected to be stable before or concurrently with 3.3V in the LDO chain |

---

## Debug Connector

| Parameter | Value |
|---|---|
| Connector | Samtec FTSH-105-01-F-DV-K (10-pin, 1.27mm pitch, dual-row, SMD) |
| Mechanical | 7.62mm x 2.54mm footprint |
| Interface | JTAG nibble bridge (SWD-compatible header with JTAG signals) |

Pinout (consistent with ARM Cortex Debug 10-pin 1.27mm standard, adapted for RISC-V JTAG):

| Pin | Signal | Direction | Notes |
|---|---|---|---|
| 1 | VTref | Output | 1.8V from VDDIO_1V8; 100Ω series resistor; identifies target IO voltage to debug probe |
| 2 | SWDIO/TMS | Bidirectional | SoC TMS pin; 10kΩ pull-up to VDDIO_1V8 |
| 3 | GND | Power | Ground reference for debug probe |
| 4 | SWDCLK/TCK | Input | SoC TCK pin; 10kΩ pull-down to GND (idles low) |
| 5 | GND | Power | Second ground; connect to GND plane |
| 6 | SWO/TDO | Output | SoC TDO pin; no pull resistor (driven by SoC) |
| 7 | NC/KEY | Mechanical key | No connect; row notch prevents incorrect connector insertion |
| 8 | TDI | Input | SoC TDI pin; 10kΩ pull-up to VDDIO_1V8 (idles high for JTAG) |
| 9 | GNDdetect | Power | Ground; used by some probes for cable detection |
| 10 | nRESET/nSRST | Bidirectional | Connected to nRST net; 100Ω series resistor; open-drain from probe; 10kΩ pull-up to VDDIO_3V3 via separate resistor on nRST net |

Pull resistors on all JTAG signals are required to prevent floating inputs when the debug
connector is unpopulated.

---

## IO Connectors and Test Points

### UART header

| Parameter | Value |
|---|---|
| Connector | 4-pin 2.54mm pitch header (Wurth 61300411121 or TE 5-146274-4) |
| Pin 1 | VCC (3.3V, 100mA max; fused with 0.1A polyfuse PTC) |
| Pin 2 | GND |
| Pin 3 | TX (SoC UART TX output; 3.3V CMOS) |
| Pin 4 | RX (SoC UART RX input; 3.3V CMOS; 100Ω series resistor for ESD protection) |

Level: 3.3V CMOS direct; no level shifter on evaluation board. Host UART adapter must be
3.3V compatible. Do not connect a 5V TTL adapter without level shifting.

### GPIO and IRQ test points

All test points use 1mm through-hole via pads (gold-plated) for oscilloscope probe ground-clip
attachment and logic analyzer flying leads:

| TP reference | Signal | Net | Voltage |
|---|---|---|---|
| TP1 | GPIO[0] | GPIO0 | 1.8V CMOS |
| TP2 | GPIO[1] | GPIO1 | 1.8V CMOS |
| TP3 | GPIO[2] | GPIO2 | 1.8V CMOS |
| TP4 | GPIO[3] | GPIO3 | 1.8V CMOS |
| TP5 | IRQ[0] | IRQ0 | 1.8V CMOS |
| TP6 | IRQ[1] | IRQ1 | 1.8V CMOS |
| TP7 | BOOT_SEL | BOOT_SEL | 1.8V CMOS; pulled down to GND via 10kΩ; jumper or solder bridge to VDDIO_1V8 to override boot mode |
| TP8 | CLK_24M | CLK_24M | 1.8V CMOS (oscillator output); 50Ω characteristic impedance trace; test point placed as a T-tap with AC-blocking capacitor (1nF 0402) in series to minimize reflection |

Each GPIO and IRQ signal has a 100Ω series resistor between the SoC pin and the test point/connector
to limit ESD injection and ringing on long probe cables.

### Display FPC connector (placeholder)

| Parameter | Value |
|---|---|
| Connector | Amphenol FCI 20455-040E-12 (40-pin 0.5mm pitch FPC/FFC, ZIF, top contact) |
| Interface | Reserved for DSI/MIPI display module or HDMI bridge adapter |
| Population | DNP (Do Not Populate) on first prototype; footprint placed for future bring-up |
| Power | Reserved 3.3V rail on pin 1 and 3.3V on pin 40; all signal pins connected to SoC display port |

---

## KiCad Project Structure

The KiCad project lives at `board/kicad/hello-demo/`. The following files must be created
and checked in before the kicad_project_release work order item can close:

```
board/kicad/hello-demo/
  hello-demo.kicad_pro          # KiCad 7/8 project file; links schematic and PCB
  hello-demo.kicad_sch          # Top-level hierarchical schematic (page 1)
  pages/
    power.kicad_sch             # Schematic page 2: power regulators and decoupling
    osc_reset.kicad_sch         # Schematic page 3: oscillator and reset supervisor
    debug_io.kicad_sch          # Schematic page 4: debug connector and UART
    connectors.kicad_sch        # Schematic page 5: USB-C, barrel jack, FPC
  hello-demo.kicad_pcb          # PCB layout file
  sym-lib-table                 # Symbol library table (project-local)
  fp-lib-table                  # Footprint library table (project-local)
  libs/
    hello-demo.kicad_sym        # Project symbol library (SoC, board-specific symbols)
    hello-demo.pretty/          # Project footprint library directory
      hello_soc_qfn64.kicad_mod # SoC footprint (derived from package vendor drawing)
      sit8924b_3225.kicad_mod   # Oscillator footprint (3.2x2.5mm, 4-pad SMD)
      max823l_sot23.kicad_mod   # Reset supervisor footprint
      samtec_ftsh105.kicad_mod  # Debug connector footprint
```

Schematic page breakdown:

- **Page 1 — SoC (hello-demo.kicad_sch)**: Top-level hierarchical sheet; instantiates the SoC
  symbol with all pins visible; connects every pin to a named net or places a no-connect marker;
  hierarchical sheet labels for each sub-page interface (power nets, CLK_24M, nRST, JTAG signals,
  UART_TX/RX, GPIO nets, IRQ nets)

- **Page 2 — Power (power.kicad_sch)**: TPS62150 (VDDCORE 0.8V), TLV74033 (VDDIO_3V3), TLV74018
  (VDDIO_1V8), USB-C power path, barrel jack path, ORing diodes, ferrite beads, all bulk and
  decoupling caps, power flags for each rail

- **Page 3 — Oscillator and Reset (osc_reset.kicad_sch)**: SiT8924B-11-18E-24.000, MAX823LEUR+T,
  manual reset button, reset LED circuit, nRST net, CLK_24M net, BOOT_SEL pull-down

- **Page 4 — Debug and IO (debug_io.kicad_sch)**: Samtec FTSH-105 debug header with all pull
  resistors, UART 4-pin header, GPIO test points TP1–TP8, series resistors on each IO signal

- **Page 5 — Connectors (connectors.kicad_sch)**: USB4135-GF-A USB-C receptacle, CUI PJ-002A
  barrel jack, Amphenol FCI 40-pin FPC (DNP), any board-edge mounting holes

---

## First-Article Test Procedure

This procedure applies to the first assembled board received from the assembly house. It must
be executed in order. Any FAIL result halts the procedure; do not proceed to the next step
until the failure is investigated and either resolved or a stop-condition log entry is created.

Required instruments:
- Bench power supply (two channels): Keysight E36313A or equivalent; 0–6V / 3A per channel
- Digital multimeter: Fluke 87V or equivalent
- Oscilloscope: 2-channel, >=200 MHz bandwidth, >=1 GSa/s (e.g., Siglent SDS1204X-E)
- Logic analyzer: 8-channel, >=24 MHz capture rate (e.g., Saleae Logic 8)
- USB-to-UART adapter: 3.3V TTL (e.g., FTDI FT232RL breakout at 3.3V)
- JTAG debug probe: J-Link EDU Mini or OpenOCD-compatible probe with 10-pin Cortex adapter
- Serial terminal: PuTTY or screen at 115200 8N1

### Step 1: Visual inspection

- Inspect all component placements for correct orientation (SoC pin 1, polarity-marked capacitors and regulators).
- Verify all QFN exposed-pad center pad is soldered (use X-ray if available, or check thermal resistance continuity with DMM).
- Inspect for solder bridges at SoC pads, regulator pads, and fine-pitch debug connector.
- Inspect for lifted leads or tombstoned passives at 0402 components.
- PASS criteria: No visible solder bridges, no missing components, all polarity markers correct.

### Step 2: Resistance check (board de-energized, no components attached)

- Set multimeter to resistance mode.
- Measure VDDCORE to GND: expected > 10kΩ (confirms no short between core supply and ground).
- Measure VDDIO_3V3 to GND: expected > 5kΩ.
- Measure VDDIO_1V8 to GND: expected > 5kΩ.
- Measure nRST to GND: expected > 10kΩ (pull-up present, no short).
- PASS criteria: All measurements above threshold. Any reading below 1kΩ indicates a solder bridge or component fault; halt and investigate before powering on.

### Step 3: Current-limited power-on (bench supply, 100mA limit per rail)

- Set bench supply channel 1: 3.3V, current limit 100mA (for VDDIO_3V3 input path).
- Set bench supply channel 2: 5V, current limit 100mA (for VDDCORE path; TPS62150 will regulate to 0.8V).
- Connect channel 2 to USB-C VBUS input pads (or use barrel jack with external 5V supply).
- Connect channel 1 to VDDIO_3V3 test point directly (bypass LDO for initial rail verification if needed), or power via VBUS and observe all three rails.
- Power on channel 2 (5V) first; observe current draw: expected < 50mA at startup (oscillator + regulator quiescent).
- Measure VDDCORE at SoC VDD pin: expected 0.8V ± 3% (0.776V–0.824V).
- Measure VDDIO_3V3 at SoC VDDIO pin or test point: expected 3.3V ± 3% (3.201V–3.399V).
- Measure VDDIO_1V8 at SoC VDDIO_1V8 pin: expected 1.8V ± 3% (1.746V–1.854V).
- PASS criteria: All rails within tolerance, no supply overcurrent latch triggered, board does not exceed 40°C surface temperature at ambient 25°C.

### Step 4: Oscillator verification

- Connect oscilloscope probe (10x, 50Ω compensation) to TP8 (CLK_24M); ground clip to nearest GND test point.
- Observe continuous clock waveform; measure: frequency (expected 24.000 MHz ± 25 ppm = 23.9994–24.0006 MHz), amplitude (expected 1.6V–1.9V peak-to-peak for 1.8V CMOS), duty cycle (expected 45%–55%), rise/fall time (expected < 5 ns, 10%–90%).
- PASS criteria: Frequency within ±25 ppm of 24 MHz, amplitude > 1.5V Vpp, no excessive ringing (< 20% overshoot above 1.8V).

### Step 5: Reset verification

- Set oscilloscope to capture a single-shot trigger on nRST rising edge (CH2 trigger, falling-edge trigger before button press or power cycle).
- Power-cycle the board or press the manual reset button (SW_RESET).
- Observe nRST pulse: expected minimum 140ms low duration (MAX823L timer), followed by clean rising edge (no chatter).
- Measure nRST low voltage: expected < 0.1V (clean logic 0). Measure nRST high voltage: expected > 3.0V (pull-up to 3.3V through 10kΩ).
- Reset LED should be off during reset assertion and on after reset deassertion.
- PASS criteria: nRST low duration >= 140ms, clean edges, correct voltage levels, LED behavior matches expected.

### Step 6: Debug bridge smoke test

- Connect J-Link EDU Mini to Samtec FTSH-105 debug header using 10-pin 1.27mm adapter cable.
- With board powered and out of reset, launch OpenOCD with target config: `target/riscv` or custom hello-soc config specifying JTAG tap IR length.
- Attempt JTAG scan: `openocd -f interface/jlink.cfg -f target/hello_soc.cfg -c "init; scan_chain; exit"`.
- Observe: JTAG chain detected, IDCODE read back as non-zero value (expected IDCODE per rtl/debug registers; confirm against hello_dbg_mmio_bridge.sv IDCODE field).
- Test nibble loopback if supported: write a known pattern to a writable debug MMIO register; read it back; confirm round-trip integrity.
- PASS criteria: OpenOCD exits 0, IDCODE is non-zero, loopback read matches written value.

### Step 7: UART smoke test

- Connect FTDI USB-to-UART adapter (3.3V mode) to UART header: adapter TX to board RX (pin 4), adapter RX to board TX (pin 3), adapter GND to board GND (pin 2); do not connect VCC pin on adapter to board (board is already powered).
- Open serial terminal at 115200 8N1, no flow control.
- Power-cycle the board; observe terminal output within 2 seconds of reset deassertion.
- Expected output: Any byte sequence or boot message from the boot ROM or initial firmware; even a single non-zero byte over UART confirms the UART peripheral and SoC are functional.
- If no output: verify UART TX with oscilloscope on TP signal; check baud rate divisor register programming in boot ROM.
- PASS criteria: At least one non-zero byte received over UART after reset deassertion without framing errors.

---

## Assembly Notes

- Solder paste: SAC305 (Sn/Ag/Cu 96.5/3.0/0.5) type 4 or type 5 powder; no-clean flux.
- Stencil: 0.15mm laser-cut stainless steel; 90% area ratio for 0402 pads; full aperture for QFN thermal pad; 80% area ratio for QFN perimeter pads (to reduce bridging risk).
- Reflow profile (SAC305): preheat 150°C–200°C @ 1–3°C/s ramp; soak 60–120s at 180°C; reflow peak 235°C–245°C; above liquidus (217°C) for 60–90s; cool 3–6°C/s max.
- Inspection: AOI after placement; X-ray inspection of SoC QFN thermal pad; visual inspection at 10x magnification for 0402 tombstoning and 1.27mm connector bridges.
- Handling: SoC is MSL 3 (sealed, desiccant, humidity indicator; bake at 125°C for 48h if floor life exceeded); store all boards in ESD bags.
- Board finish (ENIG): do not use isopropyl alcohol cleaning after reflow on ENIG boards if no-clean flux is used; use flux-specific cleaner only if aqueous flux is substituted.

---

## Known Fabrication Blockers (as of 2026-05-17)

- Package is placeholder QFN64; footprint must be regenerated from package vendor drawing before fabrication release.
- KiCad project files (`.kicad_sch`, `.kicad_pcb`) do not yet exist; see `kicad_project_release` and `board_kicad_schematic_draft` work order items.
- Power sequencing values (regulator selection, resistor values) are preliminary; subject to revision after post-route power budget is available.
- No SI/PI analysis has been performed; decoupling values and ferrite bead selections are based on typical design guidelines, not simulation results for this specific layout.
- No assembly house DFM review has been performed.
- First-article bring-up has not occurred; PASS criteria in this document are targets, not verified results.
