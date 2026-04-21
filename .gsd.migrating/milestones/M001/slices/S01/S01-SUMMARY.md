---
id: S01
parent: M001
provides:
  - Crash-safe streaming PCM writer with JSON sidecar metadata
  - WAV finalization via stdlib wave module
  - Recovery system for leftover .pcm.part files after crashes
  - WASAPI microphone capture via sounddevice
  - FakeAudioModule for deterministic testing
  - AudioSession with multi-source mixing, resampling, and streaming to disk
  - RecordingController with non-blocking UI API and worker thread
  - Widget-driven recording UI with click/drag interaction
requires: []
affects: [S02, S03]
key_files:
  - src/metamemory/audio/storage/paths.py
  - src/metamemory/audio/storage/pcm_part.py
  - src/metamemory/audio/storage/wav_finalize.py
  - src/metamemory/audio/storage/recovery.py
  - src/metamemory/audio/capture/devices.py
  - src/metamemory/audio/capture/sounddevice_source.py
  - src/metamemory/audio/capture/fake_module.py
  - src/metamemory/audio/session.py
  - src/metamemory/recording/controller.py
  - src/metamemory/widgets/main_widget.py
key_decisions:
  - "stdlib wave module for WAV headers — not hand-rolled"
  - "PCM + JSON sidecar format — human-readable crash recovery metadata"
  - "finalize_stem() defaults to delete_part=True — prevents false-positive recovery prompts"
  - "soxr.ResampleStream for streaming resampling — avoids buffering entire recording"
  - "Producer-consumer with dedicated consumer thread — non-blocking disk writes"
  - "Alpha=1 near-invisible DragSurfaceItem — enables drag from empty widget areas"
patterns_established:
  - ".pcm.part + .pcm.part.json sidecar pattern for crash-safe streaming writes"
  - "PcmPartWriter context manager with flush() for durability control"
  - "RecordingController worker thread for non-blocking stop/finalization"
  - "FakeAudioModule file-driven source for deterministic test pipelines"
  - "Click vs drag detection via 5px/300ms thresholds in Qt widget"
drill_down_paths:
  - .gsd/milestones/M001/slices/S01/S01-CONTEXT.md
  - .gsd/milestones/M001/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M001/slices/S01/tasks/T04-SUMMARY.md
verification_result: passed
completed_at: 2026-04-21
---

# S01: Audio Capture Foundation

**Crash-safe recording pipeline with WASAPI mic capture, streaming PCM writer, WAV finalization, recovery, and widget-driven UI**

## What Happened

Built the complete audio capture foundation in 10 tasks across 4 phases:

1. **Storage primitives** (T01) — `PcmPartWriter` streams int16 PCM to `.pcm.part` files with a JSON sidecar containing sample rate, channels, and sample width. `finalize_part_to_wav()` converts parts to standard WAV via stdlib `wave`. Recovery module scans for leftover `.pcm.part` files and converts them to playable `.recovered.wav` files.

2. **WASAPI capture** (T02) — Device enumeration with WASAPI hostapi detection, `MicSource` for microphone capture, `SystemSource` interface (placeholder awaiting Windows Core Audio COM), and `FakeAudioModule` for testing.

3. **Session wiring** (T03) — `AudioSession` manages multi-source recording with automatic resampling (soxr), stereo→mono downmix, source mixing (float32 sum + clip), and consumer thread for non-blocking disk writes. CLI harness and 8 automated tests.

4. **Widget integration + fixes** (T04–T10) — `RecordingController` with non-blocking stop, widget record button and source lobes, startup crash recovery prompt. Fixed FakeAudioModule endless looping, double-click requirement, crash recovery false positives, CLI fake duration, and widget drag/click interaction.

## Verification

- 33 automated tests (25 storage + 8 session)
- Manual checkpoint: mic-only recording (10s), crash recovery, 30+ min stability — all passed
- System audio blocked pending Windows Core Audio COM implementation
- All 7 UAT items verified

## Deviations

- `SystemSource` raises `AudioSourceError` instead of attempting capture — sounddevice's PortAudio doesn't expose WASAPI loopback directly
- `soxr.Resample` → `soxr.ResampleStream` (API name correction)
- `finalize_part_to_wav` signature mismatch fixed during implementation

## Files Created/Modified

- `src/metamemory/audio/storage/paths.py` — Directory resolution, filename generation
- `src/metamemory/audio/storage/pcm_part.py` — Streaming PCM writer with JSON sidecar
- `src/metamemory/audio/storage/wav_finalize.py` — PCM → WAV conversion
- `src/metamemory/audio/storage/recovery.py` — Crash recovery for partial recordings
- `src/metamemory/audio/capture/devices.py` — WASAPI device enumeration
- `src/metamemory/audio/capture/sounddevice_source.py` — MicSource, SystemSource
- `src/metamemory/audio/capture/fake_module.py` — FakeAudioModule for testing
- `src/metamemory/audio/session.py` — AudioSession, SessionConfig, SourceConfig
- `src/metamemory/recording/controller.py` — RecordingController with worker thread
- `src/metamemory/widgets/main_widget.py` — Widget with drag surface, click handling
- `tests/test_audio_storage.py` — 25 tests
- `tests/test_audio_session.py` — 8 tests
