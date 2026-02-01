---
phase: 01-audio-capture-foundation
plan: 05
subsystem: audio
tags: [audio, fake, cli, session]

requires:
  - "01-01 through 01-04 core audio implementation"
provides:
  - "Fixed fake audio duration control"
  - "Proper stop() ordering prevents race conditions"
affects: []

tech-stack.added: []
tech-stack.removed: []
tech-stack.patterns:
  - "SourceConfig with loop parameter"
  - "Stop ordering: sources before drain"

key-files.created: []
key-files.modified:
  - src/metamemory/audio/session.py
  - src/metamemory/audio/cli.py

decisions:
  - id: "loop-default-false"
    decision: "SourceConfig.loop defaults to False for natural termination"
    rationale: "Safer default - fake recordings should terminate naturally, not loop indefinitely"
    consequences: "CLI must explicitly pass loop=False (good practice)"

metrics:
  duration: "15 minutes"
  completed: "2026-02-01"
  tasks: 4
  commits: 1
---

# Phase 01 Plan 05: Fix FakeAudioModule Endless Looping Summary

## One-Liner
Fixed FakeAudioModule endless looping to create WAVs of specified duration by adding loop parameter and reordering stop() to prevent race conditions.

## What Was Delivered

### Changes Made
1. **Added loop parameter to SourceConfig** - New `loop: bool = False` field controls whether fake audio loops indefinitely
2. **Updated FakeAudioModule creation** - Changed from hardcoded `loop=True` to use `source_config.loop`
3. **CLI passes loop=False explicitly** - Fake recordings now terminate naturally after specified duration
4. **Fixed stop() ordering** - Sources stopped BEFORE drain loop to prevent race condition

### Verification
- [x] SourceConfig has loop parameter with default False
- [x] FakeAudioModule uses configured loop value from SourceConfig
- [x] CLI sets loop=False for fake recordings
- [x] Sources stopped before drain loop, preventing race condition

### Root Cause
- Hardcoded `loop=True` (session.py:367) caused fake audio to loop indefinitely
- Race condition where drain loop consumed frames while source's read thread was still adding them (sources stopped AFTER drain)
- Combined effect: 5-second recording became 3+ hours

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| loop defaults to False | Safer default for natural termination |
| CLI passes loop=False explicitly | Good practice even though default is False |
| Stop sources before drain | Prevents new frames during drain loop |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### Prerequisites Met
- [x] FakeAudioModule creates N-second WAV files
- [x] No endless looping or race conditions
- [x] Recording stops cleanly

### Blockers
None. Plan 01-05 complete.

## Technical Debt

None introduced.

## Performance Notes

Stop() ordering change improves shutdown reliability:
- Before: Potential for frames added during drain
- After: Sources stopped first, then drain completes

## Testing Notes

**Verification command:**
```bash
python -m metamemory.audio.cli --fake path/to/test.wav --seconds 5
```

**Expected result:** WAV file is approximately 5 seconds (not 3+ hours)
