# Linux NPU ML Smoke

`hello-npu-ml-smoke` is the first Linux userspace proof that the booted system
can run a basic ML-shaped workload on the local NPU block.

## Scope

The smoke tool:

- opens `/dev/hello-npu`,
- validates `OPENPHONE_HELLO_NPU_IOC_GET_CONTRACT`,
- mmaps the NPU register page through the driver,
- stages a fixed signed INT8 `2x2x3` GEMM tile into the 64-byte scratchpad,
- launches `GEMM_S8`,
- polls `CTRL_STATUS.done/error`,
- checks `C = [[-44, 8], [139, -54]]`,
- prints cycles, MACs, ops, and errors from NPU perf counters.

The matching Python runtime workload is
`HELLO_NPU_BOOT_ML_SMOKE` in `compiler/runtime/hello_npu_runtime.py`.

## Target Usage

Enable the Buildroot package:

```sh
BR2_PACKAGE_HELLO_NPU_ML_SMOKE=y
```

After Linux boots with the OpenPhone hello NPU driver loaded:

```sh
hello-npu-ml-smoke
```

Expected success shape:

```text
hello-npu-ml-smoke: PASS workload=gemm_s8_2x2x3 c=[[-44,8],[139,-54]] cycles=12 macs=12 ops=1 errors=0 result=0x...
```

Exit codes are stable for capture scripts:

| Code | Meaning |
| ---: | --- |
| `0` | GEMM completed and matched expected output |
| `2` | `/dev/hello-npu` missing or not openable |
| `3` | contract ioctl missing or mismatched |
| `4` | mmap rejected, commonly missing `CAP_SYS_RAWIO` |
| `5` | NPU completed with `CTRL_STATUS.error` |
| `6` | GEMM output mismatch |
| `7` | NPU completion timeout |

## Proof Boundary

This is local `L0_RTL_UNIT` / Linux BSP evidence only. It does not prove:

- Android NNAPI acceleration,
- TensorFlow Lite delegate execution,
- IREE or MLIR lowering,
- DMA writeback tensor execution,
- cache coherency or IOMMU isolation,
- phone-class TOPS, power, thermal, or sustained throughput.

The smoke uses the root-only mmap path because the current Linux UAPI exposes
scalar command submission and contract discovery, while the bounded GEMM tile is
still programmed through MMIO scratchpad registers. A future production ABI must
replace this with owned command buffers, explicit tensor memory ownership,
completion queues, and per-context fault isolation.

## Remaining Blockers

Local blockers now reduce to target availability:

- boot a kernel that imports `sw/linux/drivers/openphone/openphone-hello-npu.c`,
- ensure the DT node is compatible with `openphone,hello-npu`,
- run as root or with `CAP_SYS_RAWIO` for mmap,
- archive the stdout plus kernel log around probe and command execution.

Framework proof remains blocked until separate artifacts exist:

- NNAPI: `benchmarks/capabilities/hello_npu_nnapi.proof.json` plus transcripts,
- TFLite: real `benchmark_model` target binary, model hash, zero CPU fallback,
- IREE/MLIR: checked-in lowering path from an imported graph to hello NPU
  command buffers, with unsupported-op accounting.
