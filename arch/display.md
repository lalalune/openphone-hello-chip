# Display contract

The hello display block is a minimal synthesizable timing and address-generation
scaffold. It keeps the existing framebuffer-oriented MMIO contract, but it does
not fetch framebuffer contents from memory.

| Offset | Name | Access | Description |
| ---: | --- | --- | --- |
| `0x00` | `FB_BASE` | RW | Base address used to form scanout byte addresses |
| `0x04` | `MODE` | RW | `{height[15:0], width[15:0]}`; zero fields clamp to 1 |
| `0x08` | `FORMAT` | RW | FourCC-like format value; only `XR24` is accepted |
| `0x0C` | `ENABLE` | RW | Bit 0 enables scanout; disabled scanout holds counters at zero |
| `0x10` | `VSYNC` | RO | Bit 0 is the one-cycle vsync interrupt pulse |

When enabled, the block generates active-high timing outputs:

```text
scan_active
scan_hsync
scan_vsync
scan_x
scan_y
scan_fb_addr
scan_rgb
```

The current timing scaffold uses fixed porches around the programmable active
area: horizontal front/sync/back `16/96/48` pixels and vertical front/sync/back
`10/2/33` lines. `scan_fb_addr` is `FB_BASE + 4 * (scan_y * width + scan_x)`
during active pixels and zero outside the active region. The `FORMAT` register
resets to `XR24`; writes to unsupported formats are ignored because there is no
format conversion pipeline.

`scan_rgb` is a deterministic test pattern derived from `scan_x` and `scan_y`.
It is not loaded from `scan_fb_addr`. This prevents the current RTL from being
mistaken for real scanout: a production display path still needs a memory read
client, buffering or underflow handling, pixel format conversion, timing mode
programming, and a PHY or external display interface.

The first Linux driver should treat this as a simple framebuffer or DRM/KMS
scanout device. Android should initially use software rendering and a minimal
HWC path.
