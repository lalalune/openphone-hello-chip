# Benchmark Harness

The first benchmark harness lives under `benchmarks/` and is a command planner
plus thin runner for the first v0 benchmark set:

- CoreMark
- STREAM
- lmbench `bw_mem`
- lmbench `lat_mem_rd`
- fio sequential and random profiles
- TensorFlow Lite `benchmark_model` on CPU and the future hello NPU path

It is intentionally safe on a workstation without those tools installed. Planning
mode reports every command and marks unavailable binaries or blocked model
artifacts without executing anything.

## CLI Commands

List configured benchmarks and installation hints:

```sh
python3 benchmarks/run_benchmarks.py list
```

Create a dry-run report:

```sh
python3 benchmarks/run_benchmarks.py plan --report-id dry-run
```

Execute available benchmarks:

```sh
python3 benchmarks/run_benchmarks.py run \
  --report-id board-smoke-001 \
  --platform openphone-hello \
  --platform-revision dev-board-a \
  --claim-level L4_DEV_BOARD
```

Validate an existing report:

```sh
python3 benchmarks/run_benchmarks.py validate-report benchmarks/results/dry-run/report.json
```

## Dry Run

```sh
python3 benchmarks/run_benchmarks.py plan --report-id dry-run
```

The command writes:

```text
benchmarks/results/dry-run/report.json
benchmarks/results/dry-run/<benchmark>.log
```

Use `--bench <name>` to select a single benchmark. Valid names are defined in
`benchmarks/configs/benchmark_plan.json`. For compatibility, the old option-only
form still works:

```sh
python3 benchmarks/run_benchmarks.py --dry-run --report-id dry-run
```

## Real Run

Install the benchmark tools on the target host or board, then run:

```sh
python3 benchmarks/run_benchmarks.py run \
  --report-id board-smoke-001 \
  --platform openphone-hello \
  --platform-revision dev-board-a \
  --claim-level L4_DEV_BOARD
```

Missing tools are recorded as `missing_dependencies` and do not abort the whole
run unless `--strict-missing` is passed. Missing or placeholder model artifacts
are recorded as `blocked_assets` with status `blocked`; they also make
`--strict-missing` return non-zero. Failed commands, timeouts, and runner errors
return a non-zero exit status.

Expected status codes:

- `0`: report generated and no executed benchmark failed.
- `1`: at least one executed benchmark failed, timed out, or hit a runner error.
- `2`: `--strict-missing` found missing dependencies or blocked assets.
- `3`: generated or supplied report failed schema validation.

## Configuration

`benchmarks/configs/benchmark_plan.json` is the source of truth for the skeleton
commands. Keep command arrays shell-free and explicit. The runner checks:

- `requires`: executables expected on `PATH`
- `required_files`: repository-relative files, such as a TFLite model
- `timeout_seconds`: per-benchmark timeout override

The TFLite entries reference `benchmarks/models/mobile_smoke.tflite` as a tiny
smoke model artifact. The optional generator is offline-only:

```sh
python3 benchmarks/models/generate_mobile_smoke_tflite.py \
  --out benchmarks/models/mobile_smoke.tflite
```

It uses an already-installed TensorFlow package and does not download anything.
If TensorFlow is not installed, it exits with code `2` and prints/writes a
machine-readable blocker. Until a real non-proprietary model exists, plan and
run commands report those entries as `blocked` rather than passing them as real
performance. A tiny placeholder file is also blocked by the configured
`min_size_bytes` check.

The STREAM entry uses `stream_c.exe` by default to avoid confusing ImageMagick's
unrelated `stream` utility with the memory benchmark.

## Installing Or Supplying Benchmarks

For local dependency smoke testing, use the repository venv path:

```sh
make venv
.venv/bin/python -m pip install tensorflow
make benchmark-tools
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python benchmarks/run_benchmarks.py run \
  --bench coremark \
  --bench stream \
  --bench lmbench_bw_mem \
  --bench lmbench_lat_mem_rd \
  --bench fio_seq_read \
  --bench fio_rand_rw \
  --bench tflite_cpu \
  --report-id local-host-tools-pass \
  --platform openphone-local-host \
  --platform-revision venv-tools \
  --claim-level L2_ARCH_SIM \
  --metadata benchmarks/metadata/local-host-smoke.json \
  --strict-missing
```

The venv tools under `benchmarks/tools/` are host smoke wrappers. They prove the
harness can execute and parse each benchmark family on this workstation; they
are not target-board, prototype-silicon, or complete-phone performance evidence.
`tflite_hello_npu` must still fail until a real `hello-npu` NNAPI path exists,
and `simulator_arch_metrics` must still reject QEMU liveness-only data as
calibrated benchmark evidence.

| Benchmark | What the harness expects | How to provide it |
|---|---|---|
| CoreMark | `coremark` on `PATH` | Build EEMBC CoreMark for the target compiler and install or copy the executable into the benchmark user's `PATH`. |
| STREAM | `stream_c.exe` on `PATH` | Compile STREAM from source for the target, keep the binary name `stream_c.exe`, and put it on `PATH`. The name avoids colliding with ImageMagick's `stream`. |
| lmbench bandwidth | `bw_mem` on `PATH` | Build lmbench for the target and expose `bw_mem` on `PATH`. |
| lmbench latency | `lat_mem_rd` on `PATH` | Build lmbench for the target and expose `lat_mem_rd` on `PATH`. |
| fio sequential read | `fio` on `PATH` | Install fio from the target OS package manager or cross-build it. The job file is `benchmarks/configs/fio-seq-read.fio`. |
| fio random read/write | `fio` on `PATH` | Install fio from the target OS package manager or cross-build it. The job file is `benchmarks/configs/fio-rand-rw.fio`. |
| TFLite CPU | `benchmark_model` on `PATH` and `benchmarks/models/mobile_smoke.tflite` | Build TensorFlow Lite's benchmark tool and generate or supply a redistributable smoke model. Do not use proprietary app or vendor models unless the report is kept private and marked accordingly outside this harness. |
| TFLite hello NPU | NNAPI-capable `benchmark_model` and `benchmarks/models/mobile_smoke.tflite` | Build `benchmark_model` with NNAPI support, generate or supply the smoke model, and run on a platform exposing the `hello-npu` accelerator name. |

## Report Shape

The generated report is JSON and maps onto the project benchmark schema in
`docs/benchmarks/report-schema.yaml`. The runner validates generated reports
before writing them and can validate an existing report with `validate-report`.
The skeleton does not parse benchmark scores yet; it records raw output logs and
a declared primary metric for each benchmark so parsers can be added
incrementally.

Blocked model assets include stable `blocker_id`, `pipeline_visible`, and
`release_blocking` fields. Release and CI jobs should fail on any blocked asset
where both booleans are true.
