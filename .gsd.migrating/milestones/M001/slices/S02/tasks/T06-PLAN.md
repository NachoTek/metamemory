# T06: Fix transcript text repetition

**Slice:** S02 — **Milestone:** M001

## Description

Fix transcript text repetition by implementing segment tracking to only emit new/changed segments from the accumulating processor.

**Purpose:** Transcript files currently contain repeating text that grows continuously as the same audio buffer gets re-transcribed.
**Output:** Transcription processor that tracks already-emitted segments and only outputs new content.
