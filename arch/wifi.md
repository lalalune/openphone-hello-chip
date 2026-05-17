# WiFi external interface contract

The application SoC will attach to an external WiFi/Bluetooth combo module
rather than implementing RF on die. The hello chip does not bond these pins and
does not implement the SDIO host controller, Bluetooth transport ownership, or
firmware driver. This document defines the product-facing digital contract that
later padframe and board work must preserve.

## Required interface

| Group | Direction at SoC | Signals | Purpose |
| --- | --- | --- | --- |
| SDIO | bidirectional | `WIFI_SDIO_CLK`, `WIFI_SDIO_CMD`, `WIFI_SDIO_D0..D3` | Primary WiFi data path |
| Control | output | `WIFI_EN`, `WIFI_RST_N` | Module power/reset sequencing |
| Wake/IRQ | input | `WIFI_HOST_WAKE`, `WIFI_IRQ` | Module wake and interrupt notification |
| Bluetooth UART | mixed | `BT_UART_TX`, `BT_UART_RX`, `BT_UART_CTS_N`, `BT_UART_RTS_N` | Bluetooth HCI transport |
| Bluetooth PCM/I2S | mixed | `BT_PCM_CLK`, `BT_PCM_SYNC`, `BT_PCM_DIN`, `BT_PCM_DOUT` | Optional audio transport |
| Coexistence | mixed | `WIFI_COEX_REQ`, `WIFI_COEX_GRANT`, `WIFI_COEX_PRI` | Optional cellular/Bluetooth coexistence |

## Electrical assumptions

- IO voltage is `1.8 V` unless the selected module requires level shifting.
- SDIO supports SDR25 as the first bring-up mode.
- All module-facing reset and enable pins must have safe board-level defaults.
- RF, antenna, filters, crystals, shields, and regulatory design remain board/module responsibilities.

## Current integration state

The machine-readable source for this contract is
`package/wifi-external-interface.yaml`. Its current state is a product scaffold:
the pins are not bonded in the hello chip, the host controller is not
implemented, and the OS/firmware driver path is not implemented.

The maturity gates before any product WiFi claim are:

- Select a concrete WiFi/Bluetooth module and bind this contract to that module datasheet.
- Add an SDIO host controller and Bluetooth UART/PCM ownership in RTL or platform integration.
- Bond the required pins in the product padframe and cross-check package, board, and RTL names.
- Add firmware and OS driver bring-up tests for reset sequencing, SDIO enumeration, IRQ, and wake.

`make wifi-interface-check` validates the expected groups, voltages, directions,
reset defaults, duplicate-free signal names, integration-state disclaimers, and
maturity gates.
