# Security subsystem

The hello chip security subsystem provides a device lifecycle controller,
a write-once OTP/fuse shadow register bank, and a secure boot ROM that
enforces boot integrity policy based on lifecycle state.

> **Status note:** The current implementation uses placeholder cryptography
> (XOR-based hash, static device key). This is a structural scaffold for
> simulation and architecture validation only. Production derivatives must
> replace these with real cryptographic primitives (SHA-256/ECDSA for image
> authentication, hardware-generated device keys from a TRNG-seeded key
> manager). Do not claim cryptographic secure boot from this repository state.

---

## Lifecycle states

The device lifecycle is encoded as a 2-bit value stored in OTP shadow
fuse word 1 (`fuse_word1_i[1:0]`).

| State | Encoding | Description |
|---|---|---|
| `LIFECYCLE_UNLOCKED` | `2'b00` | Factory / debug. All debug access permitted. Secure boot signature check skipped. Default post-reset state. |
| `LIFECYCLE_LOCKED`   | `2'b01` | Production. Secure boot required (XOR hash must match). Debug requires auth challenge/response. JTAG disabled. |
| `LIFECYCLE_RMA`      | `2'b10` | Field return. Boot policy same as LOCKED. Limited debug re-enabled by auth challenge after correct response. |
| `LIFECYCLE_INVALID`  | `2'b11` | Fused-out / bricked. Boot always fails. All debug access denied. |

### Lifecycle transitions

Only one software-driven transition is defined:

**`UNLOCKED → LOCKED`** (requires two sequential MMIO writes plus OTP fuse agreement):

1. Write `0xC0DE_CAFE` to `LIFECYCLE_TRANSITION_KEY` (`0x1000_5004`) — arms the transition.
2. Write `0xFEED_DEAD` to `LIFECYCLE_TRANSITION_KEY` — commits, but only if OTP fuse word 1
   bits[1:0] equal `2'b01`.

All other transitions (`LOCKED → RMA`, `ANY → INVALID`) are effected by physical fuse blow
and take effect at the next power-on, reflected through OTP shadow fuse word 1.

Once `LIFECYCLE_LOCKED` is entered, JTAG is disabled (`JTAG_DISABLE` asserted) and the
debug bridge is held in synchronous reset for the remainder of the power cycle.

---

## OTP fuse map

MMIO base: `0x1000_6000`

| Fuse word | Index | Contents |
|---|---|---|
| 0 | 0 | Device serial number |
| 1 | 1 | Lifecycle target state `[1:0]`; upper 30 bits reserved |
| 2 | 2 | Root key hash `[31:0]` (placeholder, lower 32 bits) |
| 3 | 3 | Root key hash `[63:32]` (placeholder, upper 32 bits) |
| 4–7 | 4–7 | Reserved / user-defined |

Each fuse word is write-once. After the first write the corresponding bit in
`FUSE_LOCK_STATUS` is set and subsequent writes to that word are silently ignored.

### OTP shadow register map

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00`–`0x1C` | `FUSE_READ[0..7]` | RO | Read current fuse values |
| `0x20`–`0x3C` | `FUSE_WRITE[0..7]` | WO | Write fuse word (once only) |
| `0x40` | `FUSE_LOCK_STATUS` | RO | Bit n = 1 after fuse word n has been written |

---

## Secure boot flow

### Unlocked path (`LIFECYCLE_UNLOCKED`)

1. Boot ROM reads lifecycle state (UNLOCKED).
2. Signature check is skipped entirely.
3. `boot_vector_o` is driven to `0x8000_0000` on the first clock after reset.
4. `boot_fail_o` remains deasserted.

### Locked / RMA path (`LIFECYCLE_LOCKED` or `LIFECYCLE_RMA`)

1. Boot ROM receives the first 16 DRAM words (`0x8000_0000`–`0x8000_003C`) via the
   `dram_word_i[15:0]` input.
2. Computes a 32-bit XOR hash: `hash = XOR(dram_word_i[0..15])`.
3. Compares against the ROM-resident hash constant `HASH_EXPECTED = 0x1234_5678`.
4. **Hash matches:** `boot_vector_o = 0x8000_0000`, `boot_fail_o = 0`.
5. **Hash mismatch:** `boot_vector_o = 0x0`, `boot_fail_o = 1`.

When `boot_fail_o` is asserted the boot is halted. Software must treat this as a
fatal error and must not proceed to execute from DRAM.

> The XOR hash and fixed constant are placeholders. Production must use ECDSA/EdDSA
> signature verification against a public key stored in fuse words 2–3.

### Invalid path (`LIFECYCLE_INVALID`)

Boot always fails: `boot_fail_o = 1`, `boot_vector_o = 0`.

---

## Debug auth challenge/response protocol

Used to re-enable limited debug access in `LIFECYCLE_LOCKED` or `LIFECYCLE_RMA`:

1. Read the 32-bit challenge word from `DEBUG_AUTH_CHALLENGE` (`0x1000_5008`).
   The challenge is a Galois LFSR value captured once at reset de-assertion.
   It is stable for the entire power cycle.
2. Compute the expected response:
   `response = challenge XOR DEVICE_KEY`
   In the placeholder implementation, `DEVICE_KEY = 0xA5A5_5A5A`.
   A production device derives this key from immutable fuse rows.
3. Write the response to `DEBUG_AUTH_RESPONSE` (`0x1000_500C`).
4. If the response is correct, `debug_auth_granted_o` is asserted for 1024 clock cycles.
5. After 1024 cycles, `debug_auth_granted_o` deasserts automatically.
   A new challenge/response cycle is required for re-entry.

---

## Lifecycle controller register map

MMIO base: `0x1000_5000`

| Offset | Name | Access | Reset | Description |
|---:|---|---|---|---|
| `0x00` | `LIFECYCLE_STATUS` | RO | `0x0` | Current lifecycle state in bits [1:0] |
| `0x04` | `LIFECYCLE_TRANSITION_KEY` | WO | — | Write `0xC0DE_CAFE` then `0xFEED_DEAD` to attempt `UNLOCKED→LOCKED` |
| `0x08` | `DEBUG_AUTH_CHALLENGE` | RO | LFSR | 32-bit challenge word, stable per power cycle |
| `0x0C` | `DEBUG_AUTH_RESPONSE` | WO | — | Write `challenge XOR DEVICE_KEY` to grant debug access |
| `0x10` | `SECURITY_FLAGS` | RO | `0x0` | bit 0 = JTAG_DISABLED, bit 1 = DBG_MMIO_DISABLED, bit 2 = UART_BOOT_DISABLED |

---

## Updated memory map

| Region | Base | Size | Purpose |
|---|---:|---:|---|
| Boot ROM | `0x0000_0000` | `4 KiB` | Identity words + secure boot ROM |
| Peripheral control | `0x1000_0000` | `4 KiB` | ID, scratch, GPIO, timer |
| DMA | `0x1001_0000` | `4 KiB` | DMA master contract model |
| NPU | `0x1002_0000` | `4 KiB` | Small NPU datapath |
| Display | `0x1003_0000` | `4 KiB` | Framebuffer scanout controller |
| **Lifecycle** | **`0x1000_5000`** | **`4 KiB`** | **Lifecycle state + debug auth** |
| **OTP shadow** | **`0x1000_6000`** | **`4 KiB`** | **Write-once fuse bank** |
| DRAM aperture | `0x8000_0000` | `4 KiB` | SRAM-backed test DRAM |

---

## Top-level security ports

New ports added to `hello_chip_top`:

| Port | Direction | Width | Description |
|---|---|---|---|
| `LIFECYCLE_STATE` | output | 2 | Current lifecycle state |
| `DEBUG_AUTH_GRANTED` | output | 1 | Debug auth window active (1024-cycle pulse) |
| `JTAG_DISABLE` | output | 1 | JTAG/debug access disabled |
| `BOOT_FAIL` | output | 1 | Secure boot verification failed |
| `BOOT_VECTOR` | output | 32 | Validated boot entry point |

When `JTAG_DISABLE` is asserted, `hello_dbg_mmio_bridge` is held in synchronous reset,
blocking all debug MMIO transactions from reaching the SoC fabric.

---

## RTL file list

| File | Module | Description |
|---|---|---|
| `rtl/security/hello_lifecycle.sv` | `hello_lifecycle` | Lifecycle state machine, LFSR challenge, debug auth, security flags |
| `rtl/security/hello_otp_shadow.sv` | `hello_otp_shadow` | Write-once OTP/fuse shadow register bank |
| `rtl/bootrom/hello_bootrom.sv` | `hello_bootrom` | Secure boot ROM with two-path boot sequence |
| `rtl/top/hello_soc_top.sv` | `hello_soc_top` | SoC top: instantiates all IP, routes security signals |
| `rtl/top/hello_chip_top.sv` | `hello_chip_top` | Chip top: exports security ports, gates debug bridge |

---

## Required negative evidence (not yet provided)

The following test transcripts must be provided before claiming secure boot:

- Unsigned image rejection (hash mismatch in LOCKED state)
- Tampered image rejection
- Wrong-key debug auth response rejection
- Corrupt image rejection (DRAM words zero / random)
- Rollback image rejection (requires version counter in OTP, not yet implemented)
- Debug-locked transcript: JTAG unlock denied, key erasure, lifecycle/RMA policy
