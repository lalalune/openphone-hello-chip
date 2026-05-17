# Display contract

The hello display block models:

```text
framebuffer base
width
height
pixel format
enable
vsync interrupt
```

The first Linux driver should treat this as a simple framebuffer or DRM/KMS scanout device. Android should initially use software rendering and a minimal HWC path.
