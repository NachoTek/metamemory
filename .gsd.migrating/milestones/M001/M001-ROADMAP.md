# M001: meetandread MVP

**Vision:** meetandread is a Windows desktop widget-style application that provides silent, invisible audio transcription as cognitive augmentation infrastructure. It captures system audio and microphone input simultaneously, transcribing in real-time using local Whisper models with confidence-coded output.

## Success Criteria

- [ ] Real-time transcription latency < 2 seconds from speech to text display
- [ ] Widget records mic and/or system audio and produces playable WAV files
- [ ] Crash recovery detects and converts leftover `.pcm.part` files on restart
- [ ] Confidence color coding renders correctly (green/yellow/orange/red thresholds)
- [ ] All processing runs locally — no cloud dependencies required


## Slices

- [x] **S01: Audio Capture Foundation** `risk:medium` `depends:[]`
  > After this: Implement crash-safe on-disk recording primitives (paths + streaming writer + WAV finalizer + recovery).
- [x] **S02: Real Time Transcription Engine** `risk:medium` `depends:[S01]`
  > After this: Build the core transcription engine with faster-whisper integration, VAD-based audio chunking, and local agreement buffer for deduplication.
- [ ] **S03: Remove Enhancement Code** `risk:low` `depends:[S02]`
  > After this: All dual-mode enhancement code removed — enhancement.py deleted, imports/config/UI references stripped, tests passing clean.
- [x] ~~**S04: Dual Mode Enhancement Architecture** `risk:medium` `depends:[S03]`~~ — SKIPPED: dual-mode enhancement removed from project scope
- [x] ~~**S05: Dual-Mode Enhancement Validation** `risk:medium` `depends:[S04]`~~ — SKIPPED: context-only phase, no executable tasks
