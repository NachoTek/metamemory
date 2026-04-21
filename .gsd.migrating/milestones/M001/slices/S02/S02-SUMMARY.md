---
id: S02
parent: M001
provides:
  - Real-time transcription with whisper.cpp in <2s latency
  - Accumulating audio processor with 60s window and 3s silence phrase detection
  - Confidence scoring normalized to 0-100 with heuristic fallback
  - Word-level transcript storage with per-word confidence
  - Widget transcript display with confidence color coding (green/yellow/orange/red)
  - Hardware detection and model size recommendation
  - Settings persistence with JSON storage
  - Settings panel UI with model selection (tiny/base/small/AUTO)
requires:
  - slice: S01
    provides: AudioSession with on_audio_frame callback delivering 16kHz mono float32 audio
affects: [S03]
key_files:
  - src/metamemory/transcription/engine.py
  - src/metamemory/transcription/accumulating_processor.py
  - src/metamemory/transcription/streaming_pipeline.py
  - src/metamemory/transcription/audio_buffer.py
  - src/metamemory/transcription/vad_processor.py
  - src/metamemory/transcription/local_agreement.py
  - src/metamemory/transcription/confidence.py
  - src/metamemory/transcription/transcript_store.py
  - src/metamemory/transcription/post_processor.py
  - src/metamemory/transcription/enhancement.py
  - src/metamemory/config/manager.py
  - src/metamemory/hardware/detector.py
  - src/metamemory/widgets/main_widget.py
key_decisions:
  - "whisper.cpp (pywhispercpp) over faster-whisper — CPU-only, no PyTorch DLL dependencies"
  - "Accumulating approach — re-transcribe buffer for context continuity, better meeting accuracy"
  - "60s window / 2s update / 3s silence — tuned for meeting/conversation transcription"
  - "Immediate commit (no agreement buffer blocking) — real-time display prioritized"
  - "Heuristic confidence estimation — whisper.cpp doesn't expose token probabilities"
  - "Word-level storage — enables per-word confidence coloring"
patterns_established:
  - "Background inference thread with queue.Queue result delivery to UI"
  - "Accumulating audio buffer with phrase-break detection via silence timeout"
  - "Segment index tracking with deduplication to prevent duplicate text"
  - "ConfigManager with JSON persistence and smart defaults"
  - "HardwareDetector + HardwareRecommender for model size guidance"
drill_down_paths:
  - .gsd/milestones/M001/slices/S02/S02-CONTEXT.md
  - .gsd/milestones/M001/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S02/tasks/T04-SUMMARY.md
verification_result: passed
completed_at: 2026-04-21
---

# S02: Real Time Transcription Engine

**Real-time transcription with whisper.cpp, accumulating audio processing, confidence scoring, and widget display in <2s latency**

## What Happened

Built the complete transcription pipeline in 12 tasks:

1. **Core engine** (T01) — WhisperTranscriptionEngine wrapping pywhispercpp for CPU-only inference, AudioRingBuffer (30s thread-safe), VADChunkingProcessor (1.0s min chunks), LocalAgreementBuffer for deduplication, confidence normalization from Whisper log_prob to 0-100.

2. **Settings system** (T02) — ConfigManager with JSON persistence, AppSettings dataclass with TranscriptionSettings and EnhancementSettings, smart defaults, versioning.

3. **Confidence & hardware** (T03) — Confidence normalization with heuristic fallback (whisper.cpp doesn't expose token probabilities), HardwareDetector (RAM, CPU cores, frequency), HardwareRecommender mapping hardware to model sizes.

4. **Integration & widget** (T04) — RealTimeTranscriptionProcessor orchestrating all components in background thread, AccumulatingTranscriptionProcessor (60s window, 2s update, 3s silence), TranscriptStore with word-level tracking, widget transcript panel with per-word confidence coloring, settings panel with model selection.

5. **Bug fixes & polish** (T05–T12) — Fixed settings panel crash, transcript text repetition (segment index tracking), auto-scroll pause (10s on manual scroll), clean exit (ALT+F4/CTRL+C/context menu), hardware detection in settings UI, model selection persistence wiring, duplicate lines after silence fix, buffer deduplication.

## Verification

- 19 automated tests for core transcription components
- Integration tests for streaming pipeline and controller
- Manual checkpoint: recording with real mic produces transcribed text within 2s
- Confidence colors render correctly in widget

## Deviations

- Migrated from faster-whisper to whisper.cpp (pywhispercpp) — no PyTorch DLL dependencies, pure CPU
- Confidence is heuristic (text characteristics) rather than actual token probabilities — whisper.cpp binding limitation
- Enhancement code built but dual-mode enhancement removed from scope — S03 will strip it

## Files Created/Modified

- `src/metamemory/transcription/engine.py` — WhisperTranscriptionEngine (519 lines)
- `src/metamemory/transcription/accumulating_processor.py` — AccumulatingTranscriptionProcessor (775 lines)
- `src/metamemory/transcription/streaming_pipeline.py` — RealTimeTranscriptionProcessor (702 lines)
- `src/metamemory/transcription/audio_buffer.py` — AudioRingBuffer (130 lines)
- `src/metamemory/transcription/vad_processor.py` — VADChunkingProcessor (152 lines)
- `src/metamemory/transcription/local_agreement.py` — LocalAgreementBuffer (180 lines)
- `src/metamemory/transcription/confidence.py` — Confidence normalization (389 lines)
- `src/metamemory/transcription/transcript_store.py` — TranscriptStore (349 lines)
- `src/metamemory/transcription/post_processor.py` — PostProcessingQueue (473 lines)
- `src/metamemory/transcription/enhancement.py` — Enhancement system (5188 lines)
- `src/metamemory/config/manager.py` — ConfigManager
- `src/metamemory/hardware/detector.py` — HardwareDetector
- `src/metamemory/widgets/main_widget.py` — Transcript panel, settings panel
- `tests/test_transcription_engine.py` — 19 tests
- `tests/test_streaming_integration.py` — Integration tests
