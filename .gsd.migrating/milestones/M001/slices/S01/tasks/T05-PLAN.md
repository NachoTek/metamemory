# T05: Fix FakeAudioModule endless looping

**Slice:** S01 — **Milestone:** M001

## Description

Fix FakeAudioModule endless looping issue to create WAVs of specified duration.

Purpose: Fake recordings must terminate naturally after N seconds, not loop indefinitely.
Root cause: Hardcoded loop=True + race condition (drain competes with source read thread).
Output: Fixed fake recordings that create N-second WAVs cleanly.
