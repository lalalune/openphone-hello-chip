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

## Secure Boot Boundary

Current status is fail-closed scaffold only. The identity/contract ROM is not
production ROM code, does not authenticate firmware, and does not lock debug.
Do not claim secure boot from this repository state.

Required negative evidence includes Unsigned, tampered, wrong-key, corrupt, and
rollback image rejection cases. Debug locked behavior also needs a target
transcript proving debug unlock denied, key erasure, and lifecycle/RMA policy.

Exact gate terms: identity/contract ROM; not production ROM code; Do not claim
secure boot; Unsigned, tampered, wrong-key; rollback image rejection; Debug
locked.
