---
id: S01
milestone: M001
status: complete
---

# S01: Audio Capture Foundation — Context

**Retrospective context** — written after execution to capture what was built and why.

## Goal

Crash-safe on-disk recording primitives with WASAPI microphone capture, streaming PCM writer, WAV finalization, crash recovery, and widget-driven recording UI.

## Why this Slice

Foundation layer for the entire pipeline — transcription (S02) needs playable 16kHz mono WAV files produced by a reliable recording pipeline. Audio must survive crashes (`.pcm.part` + JSON sidecar pattern) so no user data is lost.

## Scope

### In Scope

- Recording directory resolution (`~/Documents/metamemory/`)
- Timestamped filename generation (`recording-YYYY-MM-DD-HHMMSS`)
- Streaming PCM writer with JSON sidecar metadata for crash recovery
- WAV finalization via stdlib `wave` module
- Recovery of leftover `.pcm.part` files on startup
- WASAPI microphone capture via `sounddevice` + PortAudio
- System audio loopback interface (placeholder — raises clear error; actual WASAPI loopback needs Windows Core Audio COM)
- `FakeAudioModule` for deterministic testing without real audio hardware
- `AudioSession` with multi-source mixing, resampling to 16kHz mono, and streaming to disk
- CLI smoke harness (`python -m metamemory.audio.cli record`)
- `RecordingController` with non-blocking stop/finalization via worker thread
- Widget-driven recording (record button, source toggle lobes)
- Startup recovery prompt for crash leftovers
- Single-click interaction (click vs drag detection with 5px/300ms thresholds)
- Drag surface for widget repositioning from empty areas
- Session-level `max_frames` cap for bounded fake recordings

### Out of Scope

- Actual WASAPI system audio loopback capture (needs Windows Core Audio COM / pycaw)
- Speaker identification
- Transcript management
- System tray integration
- macOS/Linux support

## Constraints

- All processing runs locally — no cloud dependencies
- WASAPI-first device selection on Windows (AUD-06 compliance)
- Crash safety: `.pcm.part` files must be recoverable to playable WAV even after process kill
- Recording directory defaults to `~/Documents/metamemory/`
- Target format: 16kHz mono int16 PCM (finalized as WAV)

## Integration Points

### Consumes

- `sounddevice` — PortAudio bindings for WASAPI mic capture
- `soxr` — Streaming audio resampling (48kHz → 16kHz)
- `numpy` — Frame mixing, channel downmix, float32 ↔ int16 conversion
- `wave` (stdlib) — WAV header generation

### Produces

- `src/metamemory/audio/storage/paths.py` — Directory resolution, filename generation
- `src/metamemory/audio/storage/pcm_part.py` — `PcmPartWriter`, `PcmMetadata`, crash-safe streaming
- `src/metamemory/audio/storage/wav_finalize.py` — `finalize_part_to_wav()`, `finalize_stem()`
- `src/metamemory/audio/storage/recovery.py` — `find_part_files()`, `recover_part_file()`, `recover_part_files()`
- `src/metamemory/audio/capture/devices.py` — WASAPI device enumeration, loopback probing
- `src/metamemory/audio/capture/sounddevice_source.py` — `MicSource`, `SystemSource` (placeholder)
- `src/metamemory/audio/capture/fake_module.py` — `FakeAudioModule` for testing
- `src/metamemory/audio/session.py` — `AudioSession`, `SessionConfig`, `SourceConfig`
- `src/metamemory/recording/controller.py` — `RecordingController` with non-blocking UI API
- `src/metamemory/widgets/main_widget.py` — Widget UI with record button, drag surface, lobes
- 16kHz mono WAV files in `~/Documents/metamemory/` — consumed by S02 transcription engine

## Key Decisions

- stdlib `wave` module for WAV headers (not hand-rolled) — reliable, well-tested
- PCM + JSON sidecar (not custom binary format) — human-readable, easier debugging
- Preserve originals on recovery with `.recovered.bak` suffix — safer default
- `finalize_stem()` defaults to `delete_part=True` — prevents false-positive recovery prompts on restart
- `soxr.ResampleStream` for streaming resampling — avoids buffering entire recording
- Producer-consumer with dedicated consumer thread — non-blocking disk writes
- Multi-source mixing via float32 sum + clip — simple, handles mic+system simultaneously
- `FakeAudioModule` reads WAV files — deterministic testing without audio hardware
- Alpha=1 near-invisible `DragSurfaceItem` for Qt hit-testing — enables drag from empty widget areas
- Click vs drag: 5px movement + 300ms time thresholds — prevents accidental drags during clicks

## Open Questions

- System audio loopback requires Windows Core Audio COM implementation (pycaw/comtypes) — deferred to future work
