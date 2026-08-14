# CoreSTT Performance Benchmark

Use this guide to collect comparable CoreSTT performance measurements on a
Mac and a Linux machine with an NVIDIA GPU.

Run all project commands from the `CoreSTT/` directory. Use the same source
revision, dependency versions, test duration, client counts, and audio settings
on both machines.

## Benchmark Rules

1. Install `requirements.txt` in `CoreSTT/.venv` on each machine.
2. Start each server configuration once so both models can download and warm up.
3. Exclude that first download/warmup run from steady-state results.
4. Restart the server before every scenario because scheduler statistics are
   cumulative for the life of the process.
5. Avoid unrelated CPU/GPU-heavy work during a run.
6. Run every scenario for 120 seconds with 1, 2, and 4 clients.
7. Keep `--diagnostic-logging` enabled for every compared run.

## Record the Environment

Record the Python and package versions on both machines:

```bash
.venv/bin/python -c "import platform, numpy, scipy, torch; print({'python': platform.python_version(), 'machine': platform.machine(), 'numpy': numpy.__version__, 'scipy': scipy.__version__, 'torch': torch.__version__, 'cuda': torch.cuda.is_available()})"
```

On macOS, also record:

```bash
sw_vers -productVersion
sysctl -n hw.ncpu
sysctl -n machdep.cpu.brand_string
```

On Linux, also record:

```bash
lscpu
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
```

Verify that CTranslate2 can see the NVIDIA GPU:

```bash
.venv/bin/python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"
```

The result should be at least `1` before running CUDA scenarios.

## Prepare the Results Directory

```bash
mkdir -p benchmark-results
```

Use machine and scenario names in every report filename, for example:

```text
mac-int8-default-1-client.json
linux-float16-default-4-clients.json
linux-float16-tuned-2-clients.json
```

## Mac CPU Baseline

Start the server:

```bash
.venv/bin/python server.py \
  --host 127.0.0.1 \
  --port 8020 \
  --device cpu \
  --compute-type int8 \
  --cpu-threads 4 \
  --diagnostic-logging
```

Repeat the full benchmark matrix later with `--cpu-threads 8`. Do not run both
server processes at the same time.

## NVIDIA GPU Baseline

Start the server:

```bash
.venv/bin/python server.py \
  --host 127.0.0.1 \
  --port 8020 \
  --device cuda \
  --gpu-device-index 0 \
  --compute-type float16 \
  --diagnostic-logging
```

Keep the single-GPU inference gate enabled for the baseline. It is enabled by
default and prevents final and realtime work from competing on the same GPU.

In another terminal, capture GPU utilization during each run:

```bash
nvidia-smi dmon -s pucm -d 1 > benchmark-results/linux-float16-default-gpu.txt
```

Stop `nvidia-smi dmon` after the scenario completes.

## Run the Load Test

The following command models browser input by sending 48 kHz mono audio in
40 ms packets. Change `--clients` and the output filename for each run.

```bash
.venv/bin/python -m tools.stress.harness \
  --url ws://127.0.0.1:8020/ws/transcribe \
  --clients 1 \
  --duration 120 \
  --mode stream \
  --sample-rate 48000 \
  --channels 1 \
  --chunk-ms 40 \
  --ping-interval 2 \
  --metrics \
  --report-json > benchmark-results/mac-int8-default-1-client.json
```

Run the same command with:

- `--clients 1`
- `--clients 2`
- `--clients 4`

Restart the server between runs and use a new report filename each time.

## Required Scenarios

### Default realtime

Use the Mac or NVIDIA baseline command without additional flags. This measures
the current 0.6-second realtime cadence and five-second rolling window.

### Reduced realtime workload

Add these server flags:

```bash
--realtime-processing-pause 1.0 \
--realtime-max-audio-seconds 3.0
```

This configuration should reduce repeated realtime audio processing. Compare
its update frequency and latency against the default rather than assuming it is
better for transcript quality.

### Final-only

Add this server flag:

```bash
--no-realtime-transcription
```

This isolates final inference performance. In the current implementation it
stops realtime jobs, but the realtime model is still loaded at startup.

### Mac CPU thread comparison

Run the default and reduced-workload scenarios with:

- `--cpu-threads 4`
- `--cpu-threads 8`

### NVIDIA compute-type comparison

Run the default and reduced-workload scenarios with:

- `--compute-type float16`
- `--compute-type int8_float16`

### NVIDIA inference-gate comparison

Run with the gate enabled first. If GPU memory is stable, repeat one scenario
with:

```bash
--no-single-gpu-inference-gate
```

Monitor `nvidia-smi` closely. Stop the run if GPU memory is exhausted or the
server reports inference failures. A disabled gate can improve concurrency but
can also increase contention, latency, and memory pressure.

## Benchmark Matrix

| Machine | Configuration | Clients |
|---|---|---:|
| Mac | CPU int8, default realtime, 4 threads | 1, 2, 4 |
| Mac | CPU int8, reduced realtime, 4 threads | 1, 2, 4 |
| Mac | CPU int8, default realtime, 8 threads | 1, 2, 4 |
| Mac | CPU int8, final-only | 1, 4 |
| NVIDIA | CUDA float16, gate enabled, default realtime | 1, 2, 4 |
| NVIDIA | CUDA float16, gate enabled, reduced realtime | 1, 2, 4 |
| NVIDIA | CUDA int8_float16, gate enabled, default realtime | 1, 2, 4 |
| NVIDIA | CUDA float16, final-only | 1, 4 |
| NVIDIA | CUDA float16, gate disabled | 1, 2, 4 |

The gate-disabled matrix is optional and should run only when the baseline has
comfortable GPU memory headroom.

## Metrics to Compare

The stress report stores server metrics under `serviceMetrics`. Compare these
fields across reports:

- `scheduler.workers.main.inferenceDuration.p95Ms`
- `scheduler.workers.realtime.inferenceDuration.p95Ms`
- `scheduler.workers.main.queueDelay.p95Ms`
- `scheduler.workers.realtime.queueDelay.p95Ms`
- `scheduler.workers.main.totalLatency.p95Ms`
- `scheduler.workers.realtime.totalLatency.p95Ms`
- Both workers' `busyRatio`
- Both workers' `gateWait.p95Ms`
- `scheduler.queues.realtime.coalescedRealtime`
- `scheduler.queues.realtime.staleRealtimeDropped`
- Queue `rejectedJobs`
- `resources.process.cpuPercent`
- `resources.process.rssMb`
- `resources.system.memoryPercent`
- `resources.cuda.memoryPressure`
- `resources.cuda.freeMb`
- Report `messageCounts`, warnings, errors, and exceptions

At the default 0.6-second cadence, the single realtime worker must average less
than approximately 600 ms per job for one active speaker, 300 ms for two, and
150 ms for four. Rising queue delay, coalescing, staleness, or worker busy ratio
indicates that the configured concurrency exceeds inference capacity.

## Real-Speech Validation

The current stress harness sends a 440 Hz synthetic tone. It triggers the
server's WebRTC VAD and exercises scheduling and inference, but it may decode
faster than real speech and cannot measure transcript quality.

After the synthetic matrix, perform a single-client run with the same fixed
30-60 second speech recording on both machines. The most reproducible future
improvement is to add a `--wav PATH` option to the stress harness so it can
stream identical speech audio and report the same metrics automatically.

Until that option exists, use the browser microphone console for real speech:

1. Start the server with `--diagnostic-logging`.
2. Open `http://127.0.0.1:8020`.
3. Speak or play the same test script for the same duration.
4. Export the diagnostics session as JSONL or CSV from the dashboard.

## Result Review

Keep the following together for analysis:

- Environment information from each machine.
- Every stress-harness JSON report.
- NVIDIA `dmon` output for GPU scenarios.
- Browser JSONL or CSV exports from real-speech runs.
- Server logs containing inference and resource diagnostics.

Compare steady-state inference duration first, then queue delay, total latency,
coalescing/staleness, resource saturation, and error counts. Do not select a
configuration based only on connection or ping latency.
