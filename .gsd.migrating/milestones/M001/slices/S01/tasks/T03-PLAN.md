# T03: Session wiring

**Slice:** S01 — **Milestone:** M001

## Description

Implement a recording session manager that can consume mic/system/fake sources, resample/mix to 16kHz mono, stream to disk, and finalize to WAV.

Purpose: Deliver the core "start -> stream -> stop -> playable WAV" pipeline (AUD-04, AUD-05, AUD-07, and foundations for AUD-01/02/03/08).
Output: Session module + CLI harness + automated end-to-end tests using FakeAudioModule.
