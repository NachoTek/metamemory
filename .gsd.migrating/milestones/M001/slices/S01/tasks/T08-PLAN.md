# T08: Fix crash recovery false positive

**Slice:** S01 — **Milestone:** M001

## Description

Fix crash recovery false positive by cleaning up .pcm.part files after successful finalization.

Purpose: Recovery should only prompt when there are actual crash leftovers, not on every startup.
Root cause: finalize_stem() called with default delete_part=False, leaving .pcm.part files after successful WAV creation. On next startup, has_partial_recordings() detects these as crash leftovers.
Output: Clean recordings directory after normal shutdown, no false positive prompts.
