# Security model

The hello chip has no security boundary. It only reserves the architectural slot for:

```text
boot ROM
management core
debug policy
fuse/OTP abstraction
image authentication hooks
reset and clock ownership
```

The first full SoC should implement structural separation before implementing a rich secure enclave.
