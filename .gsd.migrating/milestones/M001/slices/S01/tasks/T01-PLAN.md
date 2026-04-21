# T01: Crash-safe audio storage

**Slice:** S01 — **Milestone:** M001

## Description

Implement crash-safe on-disk recording primitives (paths + streaming writer + WAV finalizer + recovery).

Purpose: Make audio durable (AUD-07) before wiring real capture.
Output: Storage modules + automated tests proving a recovered WAV is playable.
