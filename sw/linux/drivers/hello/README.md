# hello NPU Linux Driver ABI

This driver exposes the prototype hello NPU MMIO block as `/dev/hello-npu`.
The ABI is intentionally small and fail-closed: userspace can submit scalar
commands, submit one bounded INT8 GEMM tile, and read hardware performance
counters. It is sufficient for a Linux userspace ML smoke, but it is not a
TensorFlow Lite, NNAPI, IREE, or production compiler ABI.

## Device Node

- Driver compatible: `openphone,hello-npu`
- Device node: `/dev/hello-npu`
- Backing MMIO base: `HELLO_NPU_BASE`
- Implemented MMIO window: 256 bytes
- Scratchpad window: 64 bytes at `HELLO_NPU_SCRATCH0_OFFSET`

The legacy `read(2)` path returns the current `RESULT` register as text. New
runtime smoke commands must use the ioctls below.

## Ioctls

All structs use Linux fixed-width integer types and native kernel ioctl layout.
The Python reference runtime computes the same request numbers in
`compiler/runtime/hello_npu_runtime.py`.

```c
#define HELLO_NPU_IOC_MAGIC 'H'
#define HELLO_NPU_IOC_RUN_CMD _IOWR(HELLO_NPU_IOC_MAGIC, 0x01, struct hello_npu_cmd)
#define HELLO_NPU_IOC_RUN_GEMM_S8 _IOWR(HELLO_NPU_IOC_MAGIC, 0x02, struct hello_npu_gemm_s8)
#define HELLO_NPU_IOC_GET_PERF _IOR(HELLO_NPU_IOC_MAGIC, 0x03, struct hello_npu_perf)
```

`HELLO_NPU_IOC_RUN_CMD` submits scalar opcodes such as `DOT4_S8`:

```c
struct hello_npu_cmd {
        __u32 opcode;
        __u32 a;
        __u32 b;
        __u32 acc;
        __u32 result;
        __u32 status;
};
```

`HELLO_NPU_IOC_RUN_GEMM_S8` submits one bounded INT8 tile:

```c
struct hello_npu_gemm_s8 {
        __u32 m;
        __u32 n;
        __u32 k;
        __s8 a[21];
        __s8 b[21];
        __s32 c[9];
        __u32 status;
};
```

Accepted GEMM dimensions are `1 <= M,N <= 3` and `1 <= K <= 7`. The driver
packs A and B into the 64-byte scratchpad and returns C as signed int32. Any
dimension that cannot fit the scratchpad returns `-EINVAL` before launching
hardware.

`HELLO_NPU_IOC_GET_PERF` returns the counter registers:

```c
struct hello_npu_perf {
        __u32 cycles;
        __u32 macs;
        __u32 ops;
        __u32 errors;
        __u32 unsupported_ops;
};
```

## Userspace Smoke Command

Run this only on a Linux target with the driver loaded and `/dev/hello-npu`
present:

```sh
python3 compiler/runtime/hello_npu_runtime.py smoke \
  --backend=linux-ioctl \
  --device=/dev/hello-npu \
  --case=all
```

The command emits JSON with schema `openphone.hello_npu_runtime_smoke.v1`.
Without the device node it exits non-zero with `status=blocked` and
`blocked_reason=missing_device_node`. That blocked result is expected on host
machines and must not be converted into hardware evidence.

The matching benchmark plan entry is `hello_npu_linux_runtime_smoke`. It proves
only that handwritten DOT4_S8 and GEMM_S8 vectors can run through the Linux
driver/runtime path. It does not prove TFLite delegation, NNAPI acceleration,
large tensor DMA, sustained performance, or phone-comparable TOPS.
