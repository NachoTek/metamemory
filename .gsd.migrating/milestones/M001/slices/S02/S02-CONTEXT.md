---
id: S02
milestone: M001
status: complete
---

# S02: Real Time Transcription Engine — Context

**Retrospective context** — written after execution to capture what was built and why.

## Goal

Real-time transcription engine that captures audio from S01's AudioSession, transcribes it with local Whisper models in <2s latency, and delivers confidence-coded text to the widget display.

## Why this Slice

S01 produces 16kHz mono WAV files but they're silent until transcribed. S02 turns raw audio into the cognitive augmentation output the user actually sees — real-time text with confidence coloring. It unblocks S03 (removing enhancement code that depends on this slice's architecture).

## Scope

### In Scope

- Whisper transcription engine wrapping whisper.cpp (via pywhispercpp) for CPU-only inference
- AudioRingBuffer for thread-safe audio accumulation (30s window)
- VADChunkingProcessor for intelligent audio chunking (1.0s minimum chunk)
- AccumulatingTranscriptionProcessor — accumulates audio over time, re-transcribes for context continuity, detects phrase breaks via 3s silence timeout
- RealTimeTranscriptionProcessor — alternative pipeline orchestration with enhancement queue integration
- LocalAgreementBuffer for deduplication and text stability
- Confidence scoring: Whisper log_prob normalized to 0-100 scale with heuristic fallback
- Hardware detection (RAM, CPU cores, frequency) with model size recommendations
- Settings persistence system (JSON storage, versioning, smart defaults)
- Settings panel UI with model selection (tiny/base/small/AUTO)
- TranscriptStore with word-level tracking (text, timestamps, confidence, is_enhanced flag)
- Widget transcript display with per-word confidence coloring (green → yellow → orange → red)
- Auto-scroll pause (10s) when user manually scrolls up
- Clean application exit (context menu, ALT+F4, CTRL+C, position persistence)
- Buffer deduplication to prevent duplicate lines after silence
- PostProcessingQueue for stronger model transcription after recording stops
- Enhancement queue and worker pool architecture (background, low-confidence segments)

### Out of Scope

- Actual enhancement model execution (dual-mode enhancement removed from project scope — S03 removes enhancement code)
- Speaker identification
- Transcript file management (save/load/search)
- GPU/CUDA support (CPU-only via whisper.cpp)
- System audio loopback (deferred from S01)

## Constraints

- All processing runs locally on CPU — no cloud, no GPU required
- <2s latency from speech to text display (success criterion)
- whisper.cpp requires file-path input (temp WAV files per chunk)
- Python GIL means inference blocks — must run in background thread
- 16kHz mono float32 input expected from S01's AudioSession

## Integration Points

### Consumes

- `AudioSession.on_audio_frame` callback — 16kHz mono float32 numpy arrays from S01's consumer thread
- `PcmPartWriter` / WAV finalization from S01 (temp files for whisper.cpp input)
- `ConfigManager` for settings persistence (model size, enhancement threshold)

### Produces

- `src/metamemory/transcription/engine.py` — `WhisperTranscriptionEngine` wrapping pywhispercpp
- `src/metamemory/transcription/audio_buffer.py` — `AudioRingBuffer` (thread-safe, 30s window)
- `src/metamemory/transcription/vad_processor.py` — `VADChunkingProcessor` (1.0s minimum chunks)
- `src/metamemory/transcription/local_agreement.py` — `LocalAgreementBuffer` for deduplication
- `src/metamemory/transcription/accumulating_processor.py` — `AccumulatingTranscriptionProcessor` (primary pipeline)
- `src/metamemory/transcription/streaming_pipeline.py` — `RealTimeTranscriptionProcessor` (alternative with enhancement)
- `src/metamemory/transcription/confidence.py` — Confidence normalization and `should_enhance()`
- `src/metamemory/transcription/transcript_store.py` — `TranscriptStore` with `Word` and `Segment` dataclasses
- `src/metamemory/transcription/post_processor.py` — `PostProcessingQueue` for post-recording transcription
- `src/metamemory/transcription/enhancement.py` — Enhancement queue, worker pool, processor (to be removed in S03)
- `src/metamemory/config/` — `ConfigManager`, `AppSettings`, persistence layer
- `src/metamemory/hardware/` — `HardwareDetector`, `HardwareRecommender`
- Widget transcript panel with per-word confidence coloring
- Settings panel with model selection UI

## Key Decisions

- **whisper.cpp (pywhispercpp) over faster-whisper** — CPU-only, no PyTorch DLL dependencies, smaller footprint
- **Accumulating approach over chunk-by-chunk** — Re-transcribe accumulated buffer for context continuity; better accuracy for meetings
- **60s window / 2s update frequency / 3s silence timeout** — Tuned for meeting/conversation transcription
- **Immediate commit (no agreement buffer blocking)** — Real-time display prioritized over text stability
- **Heuristic confidence estimation** — whisper.cpp doesn't expose token probabilities directly; fallback based on text characteristics
- **Word-level storage** — Enables per-word confidence coloring and future enhancement marking
- **Background inference thread** — Avoids blocking audio capture or UI
- **Queue-based result delivery** — `queue.Queue` from processing thread to UI thread

## Open Questions

- Enhancement code (enhancement.py, EnhancementQueue, EnhancementWorkerPool) exists but dual-mode enhancement was removed from scope — S03 will remove it
- System audio loopback still needs Windows Core Audio COM implementation
