# Display contract

The hello display block is a minimal synthesizable timing, address-generation,
and framebuffer-fetch scaffold. It keeps the existing framebuffer-oriented MMIO
contract and exposes a narrow read-side client interface that can be coupled to
DRAM or a verification memory model.

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `FB_BASE` | RW | Base address used to form scanout byte addresses |
| `0x04` | `MODE` | RW | `{height[15:0], width[15:0]}`; zero fields clamp to 1 |
| `0x08` | `FORMAT` | RW | FourCC-like format value; only `XR24` is accepted |
| `0x0C` | `ENABLE` | RW | Bit 0 enables scanout; disabled scanout holds counters at zero |
| `0x10` | `VSYNC` | RO | Bit 0 is the one-cycle vsync interrupt pulse |
| `0x14` | `UNDERFLOW_COUNT` | RW1C-like | Counts active pixels where framebuffer data was not ready; any write clears |
| `0x18` | `FETCHED_PIXEL_COUNT` | RW1C-like | Counts active pixels fetched from the framebuffer client; any write clears |

When enabled, the block generates active-high timing outputs:

```text
scan_active
scan_hsync
scan_vsync
scan_x
scan_y
scan_fb_addr
scan_rgb
fb_read_valid
fb_read_addr
fb_read_data
fb_read_ready
```

The current timing scaffold uses fixed porches around the programmable active
area: horizontal front/sync/back `16/96/48` pixels and vertical front/sync/back
`10/2/33` lines. During active pixels, `fb_read_valid` is asserted and
`scan_fb_addr`/`fb_read_addr` are `FB_BASE + 4 * (scan_y * width + scan_x)`.
Both addresses are zero outside the active region.

The `FORMAT` register resets to `XR24` and writes to unsupported formats are
ignored. `XR24` scanout treats each fetched word as `0x00RRGGBB` and drives
`scan_rgb` as `{R, G, B}` from `fb_read_data[23:0]` when `fb_read_ready` is high.
If an active pixel is not ready, `scan_rgb` is driven black for that pixel and
`UNDERFLOW_COUNT` increments. Successful active-pixel reads increment
`FETCHED_PIXEL_COUNT`.

The top-level hello-chip scope connects the framebuffer client to the
debug-visible SRAM-backed DRAM aperture at `0x8000_0000`. In-aperture aligned
read addresses return the corresponding framebuffer word; out-of-aperture or
unaligned active scanout addresses deassert `fb_read_ready`, drive black for
that pixel, and increment `UNDERFLOW_COUNT`. Verification covers both the
standalone client contract and the top-level memory-coupled scanout path.

This is still a one-word-at-a-time SRAM model, not a production display memory
client. A real shared memory/interconnect scanout port still needs buffering,
latency tolerance, bandwidth coverage, and format expansion beyond `XR24`.

The first Linux driver should treat this as a simple framebuffer or DRM/KMS
scanout device. Android should initially use software rendering and a minimal
HWC path.
