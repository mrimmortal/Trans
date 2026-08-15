# CoreSTT Issue Tracker

This tracker consolidates the performance, correctness, compatibility, and
cleanup findings from the repository audit. Update an item's status and check
its acceptance criteria as work progresses.

## Status Legend

- `Open` — confirmed issue with no fix implemented.
- `Benchmark required` — evidence suggests an issue, but target-hardware data
  is required before changing behavior.
- `Decision required` — product or compatibility direction is required.
- `Blocked` — cannot proceed without an external dependency or decision.
- `Done` — implemented and validated.

## Priority Summary

| ID | Priority | Status | Title |
|---|---|---|---|
| PERF-001 | P0 | Open | Realtime rolling-window inference amplifies model work |
| PERF-002 | P0 | Open | One serial realtime worker serves up to four speakers |
| PERF-003 | P1 | Done | Realtime model loads when realtime transcription is disabled |
| CI-001 | P1 | Open | GitHub Actions targets a missing project tree |
| ENGINE-001 | P1 | Open | Unavailable OpenAI API engine is advertised as supported |
| PERF-004 | P1 | Benchmark required | CPU fallback runs two competing model workers |
| PERF-005 | P1 | Open | Realtime degradation threshold has no runtime effect |
| PERF-006 | P1 | Benchmark required | Long final segments can create high final latency |
| PERF-007 | P2 | Benchmark required | Batch size one may add ineffective batching overhead |
| PERF-008 | P2 | Open | `num_workers` does not increase scheduler consumers |
| CONFIG-001 | P2 | Open | Realtime batch-size runtime classification is misleading |
| CONFIG-002 | P2 | Decision required | Fixed model names prevent model-size tuning |
| BENCH-001 | P2 | Done | Stress harness lacks repeatable real-speech input |
| COMPAT-001 | P2 | Decision required | Exported legacy client uses an incompatible server protocol |
| TOOL-001 | P2 | Decision required | Kroko installer is undocumented and unreferenced |
| CORE-001 | P2 | Open | Stdout relay plumbing appears inactive |
| CLEAN-001 | P3 | Open | Verified dead code and unused imports remain |
| ARCH-001 | P3 | Decision required | Cohere and Granite wrappers add behavior-free indirection |

## Performance Issues

### PERF-001 — Realtime rolling-window inference amplifies model work

- **Priority:** P0
- **Status:** Open
- **Area:** Realtime inference

The direct WebSocket session retranscribes a rolling audio window every
`realtime_processing_pause`. With the defaults, it begins at 0.8 seconds,
runs every 0.6 seconds, and repeatedly processes up to five seconds of audio.

Synthetic analysis of a 30-second utterance produced:

- 47 realtime jobs.
- 218.48 seconds of realtime model input.
- 30 seconds of final model input.
- 248.48 total model-audio seconds, or 8.28 times the source duration.

**Evidence:**

- `CoreSTT/server.py`, `_maybe_create_realtime_job_locked()`.
- `CoreSTT/CoreSTT/server/settings.py`, realtime cadence/window defaults.
- `docs/PERFORMANCE_BENCHMARK.md`.

**Proposed direction:**

Benchmark a one-second cadence and three-second window first. Longer term,
evaluate incremental or overlap-based decoding that does not repeatedly decode
the complete rolling window.

**Acceptance criteria:**

- [ ] Mac and NVIDIA baselines are recorded using the benchmark guide.
- [ ] Realtime model workload is reduced by at least 50% in the target case.
- [ ] Interim update latency remains within the agreed product target.
- [ ] Transcript stability and final text are compared with the baseline.
- [ ] Focused session/scheduler tests cover the selected behavior.

### PERF-002 — One serial realtime worker serves up to four speakers

- **Priority:** P0
- **Status:** Open
- **Area:** Scheduler capacity

The realtime queue has one consumer thread, while the server permits four
simultaneous active speakers. At the default 0.6-second cadence, average
realtime inference must finish within approximately 600 ms for one speaker,
300 ms for two, or 150 ms for four to avoid sustained backlog.

**Evidence:**

- `CoreSTT/CoreSTT/server/inference.py`, `SharedEngineWorker._worker()`.
- `CoreSTT/CoreSTT/server/settings.py`, `max_active_speakers=4`.

**Proposed direction:**

Establish per-device capacity limits from benchmarks. If four-speaker realtime
service is required, evaluate additional engine workers, process replicas, or
GPU-aware sharding instead of only increasing queue depth.

**Acceptance criteria:**

- [ ] Sustainable client counts are documented for Mac and NVIDIA targets.
- [ ] Realtime queue-delay p95 remains below the selected service target.
- [ ] Coalesced, stale, and rejected jobs remain within agreed limits.
- [ ] Admission defaults match measured capacity.

### PERF-003 — Realtime model loads when realtime transcription is disabled

- **Priority:** P1
- **Status:** Done
- **Area:** Startup and memory

Resolved: `--no-realtime-transcription` now creates a final-only scheduler and
does not create the realtime queue, worker, model load/warmup path, CUDA gate,
recorder executor, callbacks, or recorder realtime thread.

**Resolution:**

The flag is startup-only, the scheduler reports `final-only`, and final
inference remains available without allocating realtime resources.

**Acceptance criteria:**

- [x] Final-only startup does not instantiate the realtime engine.
- [x] Final-only mode omits all scheduler and recorder realtime resources.
- [x] Final transcription still works.
- [x] Scheduler metrics report `final-only` with no realtime queue or worker.
- [x] Tests cover startup, shutdown, rejection, and final-only submission.

### PERF-004 — CPU fallback runs two competing model workers

- **Priority:** P1
- **Status:** Benchmark required
- **Area:** CPU inference

When CUDA is unavailable, both final and realtime engines run on CPU. The
single-GPU inference gate does not serialize CPU work, so both CTranslate2
models may compete for CPU threads and memory bandwidth.

**Proposed direction:**

Benchmark CPU thread counts, final-only mode, and optional CPU inference
serialization. Do not change concurrency until measured on the target Mac.

**Acceptance criteria:**

- [ ] CPU thread counts 4 and 8 are benchmarked on the target Mac.
- [ ] Concurrent final/realtime CPU utilization and latency are recorded.
- [ ] The chosen setting improves p95 latency without reducing throughput.

### PERF-005 — Realtime degradation threshold has no runtime effect

- **Priority:** P1
- **Status:** Open
- **Area:** Overload control

`realtime_degradation_threshold_ms` is accepted, exposed in limits, and
runtime-configurable, but no scheduler or session logic uses it to change
behavior.

**Proposed direction:**

Either remove the unused setting or implement explicit adaptive behavior, such
as skipping interim work, increasing cadence, or reducing the realtime window
when queue or latency thresholds are exceeded.

**Acceptance criteria:**

- [ ] The setting has documented behavior or is removed from public config.
- [ ] Tests cover threshold crossing and recovery.
- [ ] Overload handling preserves final transcription priority.

### PERF-006 — Long final segments can create high final latency

- **Priority:** P1
- **Status:** Benchmark required
- **Area:** Final inference

Continuous recordings can reach 30 seconds before forced finalization. The
complete segment is then processed by the fixed `small.en` final model.

**Proposed direction:**

Measure final latency for 5-, 10-, 20-, and 30-second speech samples. Adjust
segmentation only if target-hardware results exceed the agreed latency goal.

**Acceptance criteria:**

- [ ] Final latency and real-time factor are measured by audio duration.
- [ ] A maximum segment duration is selected from measured results.
- [ ] Segmentation changes preserve transcript continuity.

### PERF-007 — Batch size one may add ineffective batching overhead

- **Priority:** P2
- **Status:** Benchmark required
- **Area:** Faster-Whisper adapter

Both default batch sizes are `1`, which still wraps the model in
`BatchedInferencePipeline`. Short realtime windows may contain only one model
chunk, leaving no useful parallel batch.

**Proposed direction:**

A/B test batch size `0` against `1` for realtime and final workloads on both
target machines. Preserve the current default until measurements exist.

**Acceptance criteria:**

- [ ] Startup memory, inference p50/p95, and transcript output are compared.
- [ ] The selected default is documented for CPU and CUDA.

### PERF-008 — `num_workers` does not increase scheduler consumers

- **Priority:** P2
- **Status:** Open
- **Area:** Scheduler configuration

Each engine is called from one serial `SharedEngineWorker` thread. Increasing
Faster-Whisper `num_workers` does not create additional queue consumers or
parallel calls into the same model in the current architecture.

**Proposed direction:**

Clarify the setting's actual scope. If parallel model calls are required,
implement and test explicit scheduler concurrency or scale through replicas.

**Acceptance criteria:**

- [ ] Documentation no longer implies that `num_workers` scales queue workers.
- [ ] Any parallel inference design includes memory and fairness limits.

## Configuration and Benchmark Issues

### CONFIG-001 — Realtime batch-size runtime classification is misleading

- **Priority:** P2
- **Status:** Open
- **Area:** Runtime configuration

`realtime_batch_size` is classified as applying to new sessions, but the direct
session path uses a shared realtime engine initialized at server startup.
Changing the setting after startup does not rebuild that engine.

**Acceptance criteria:**

- [ ] Classify the setting as startup-only, or safely rebuild/apply it.
- [ ] Runtime configuration tests verify actual engine behavior.
- [ ] The API contract reports the correct application scope.

### CONFIG-002 — Fixed model names prevent model-size tuning

- **Priority:** P2
- **Status:** Decision required
- **Area:** Model configuration

Settings validation requires `small.en` for final transcription and `tiny.en`
for realtime transcription. This protects fixed model roles but prevents
model-size performance experiments and conflicts with generic diagnostic advice
to reduce model size.

**Acceptance criteria:**

- [ ] Decide whether fixed models remain a product requirement.
- [ ] Diagnostics recommend only supported tuning actions.
- [ ] Any model configurability change includes compatibility tests and docs.

### BENCH-001 — Stress harness lacks repeatable real-speech input

- **Priority:** P2
- **Status:** Done
- **Area:** Performance testing

Resolved: the harness accepts validated PCM WAV input, streams it at real-time
cadence, waits for final messages, and records transcript text. Platform
runners can record a confirmed local microphone sample when the default WAV is
missing.

**Resolution:**

Normal scenarios stream the WAV once; soak scenarios loop it for the requested
duration without changing the WebSocket protocol.

**Acceptance criteria:**

- [x] A WAV can be streamed without changing the WebSocket contract.
- [x] Unsupported WAV formats fail with clear errors.
- [x] The same fixture produces comparable reports on Mac and NVIDIA Linux.
- [x] Stress-harness tests cover WAV validation, chunking, and reporting.

## Correctness and CI Issues

### CI-001 — GitHub Actions targets a missing project tree

- **Priority:** P1
- **Status:** Open
- **Area:** Continuous integration

`.github/workflows/medical-dictation-pipeline.yml` runs commands under a
`medical-dictation/` directory that is absent from this checkout. The workflow
does not validate the active CoreSTT package and tests.

**Acceptance criteria:**

- [ ] Confirm whether the missing project should exist in this repository.
- [ ] Remove the unrelated workflow or replace it with CoreSTT validation.
- [ ] CI runs the documented CoreSTT unit-test command.
- [ ] CI does not download models for ordinary unit tests.

### ENGINE-001 — Unavailable OpenAI API engine is advertised as supported

- **Priority:** P1
- **Status:** Open
- **Area:** Engine registry

The engine factory and public server configuration list `openai_api`, but its
constructor always raises because request handling is not implemented.

**Acceptance criteria:**

- [ ] Remove `openai_api` from the supported registry until implemented, or
      implement the engine fully.
- [ ] `/api/config` lists only usable engines.
- [ ] Factory and server tests cover the selected behavior.

## Compatibility and Orphaned Code

### COMPAT-001 — Exported legacy client uses an incompatible server protocol

- **Priority:** P2
- **Status:** Decision required
- **Area:** Public package API

`AudioToTextRecorderClient` uses separate control/data WebSockets on ports 8011
and 8012 and attempts to launch `stt-server`. The active server uses one
WebSocket at `/ws/transcribe` on the configured FastAPI port. The legacy client
is publicly exported but has no current documentation or tests.

**Acceptance criteria:**

- [ ] Confirm whether external consumers still use the legacy client.
- [ ] Deprecate/remove it or migrate it to the current protocol.
- [ ] Preserve or intentionally version the public package contract.
- [ ] Remove client-only dependencies if the client is deleted.

### TOOL-001 — Kroko installer is undocumented and unreferenced

- **Priority:** P2
- **Status:** Decision required
- **Area:** Tooling

`CoreSTT/CoreSTT/install_kroko.py` contains a large standalone installer, but no
current documentation, package entrypoint, or source reference invokes it.

**Acceptance criteria:**

- [ ] Confirm whether the installer is supported.
- [ ] Remove it, or move it under tools and document an executable command.
- [ ] Supported installer behavior has focused tests or a documented manual
      validation procedure.

### CORE-001 — Stdout relay plumbing appears inactive

- **Priority:** P2
- **Status:** Open
- **Area:** Recorder worker runtime

The transcription worker activates print forwarding only when its imported
module name is `__main__`. That condition is not reached through documented
worker startup. The recorder still creates an additional pipe and polling
thread for stdout messages.

**Acceptance criteria:**

- [ ] Confirm the print hook is inactive in thread and process worker modes.
- [ ] Remove the relay plumbing or activate it through an explicit worker flag.
- [ ] Startup/shutdown tests confirm no leaked threads or blocked pipes.

## Cleanup Issues

### CLEAN-001 — Verified dead code and unused imports remain

- **Priority:** P3
- **Status:** Open
- **Area:** General cleanup

Confirmed cleanup candidates include:

- Unused `find_tail_match_in_text()`.
- Unused legacy-client ANSI color class and timestamp assignment.
- Unreachable sample-rate fallback code in `audio_input.py`.
- No-op wake-word expression and unused assignments.
- Unused recording/lifecycle variables.
- Unused Omnilingual model-name constants.
- Unused imports in `server.py`, `safepipe.py`,
  `realtime_text_stabilizer.py`, and the stress harness.

**Acceptance criteria:**

- [ ] Each symbol is searched before removal.
- [ ] Public compatibility exports are not removed accidentally.
- [ ] Focused tests and the full unit suite pass after cleanup.
- [ ] No unrelated formatting or refactoring is included.

### ARCH-001 — Cohere and Granite wrappers add behavior-free indirection

- **Priority:** P3
- **Status:** Decision required
- **Area:** Engine architecture

The Cohere and Granite adapter modules subclass shared implementations without
adding behavior. Direct factory registration could reduce indirection, but
external imports of the existing module paths may exist.

**Acceptance criteria:**

- [ ] Confirm whether the wrapper module paths are public compatibility points.
- [ ] Remove wrappers only when imports and engine behavior remain compatible.
- [ ] Factory tests cover the final registration paths.

## Recommended Execution Order

1. Run the benchmark matrix in `docs/PERFORMANCE_BENCHMARK.md`.
2. Address `PERF-001` and `PERF-002` using measured target-hardware limits.
3. Fix `PERF-003`, `CI-001`, and `ENGINE-001` as isolated changes.
4. Resolve configuration correctness items before exposing new tuning controls.
5. Make compatibility decisions for the legacy client and Kroko installer.
6. Complete low-risk dead-code cleanup last.

## Validation Baseline

From `CoreSTT/`:

```bash
.venv/bin/python -m unittest discover tests
```

Performance-related changes should also run the applicable scenarios from
`docs/PERFORMANCE_BENCHMARK.md` and retain the JSON reports used for comparison.
