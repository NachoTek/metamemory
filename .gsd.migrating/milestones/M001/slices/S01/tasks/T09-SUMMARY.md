---
id: T09
parent: S01
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# T09: Plan 09

**# Phase 1 Plan 9: CLI Fake Duration Fix Summary**

## What Happened

# Phase 1 Plan 9: CLI Fake Duration Fix Summary

**Session-level frame cap (max_frames) that enforces requested recording duration regardless of source emission speed, with regression test preventing full-file-copy bug**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-01T22:45:00Z
- **Completed:** 2026-02-01T22:53:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `max_frames: Optional[int]` to `SessionConfig` with documentation
- Implemented discard-mode logic in `AudioSession._consumer_loop()` to enforce frame cap
- Truncated partial chunks that would exceed cap for exact duration targeting
- Plumbed CLI `--seconds` into `SessionConfig.max_frames` calculation
- Created regression test that verifies 9s input + --seconds 5 = exactly 5s output
- Fixed UAT Test 1 failure: fake recording now produces correct duration WAV

## Task Commits

Each task was committed atomically:

1. **Task 1: Add max_frames to SessionConfig and consumer loop** - `812fd1e` (feat)
2. **Task 2: Plumb CLI --seconds into SessionConfig.max_frames** - `10158b8` (feat)
3. **Task 3: Add regression test for CLI fake duration** - `9eb4038` (test)

**Plan metadata:** (to be committed after SUMMARY)

## Files Created/Modified

- `src/metamemory/audio/session.py` - Added max_frames field to SessionConfig, implemented frame cap logic in _consumer_loop with discard_mode for clean shutdown
- `src/metamemory/audio/cli.py` - Added max_frames calculation from args.seconds, passed to SessionConfig
- `tests/test_cli_fake_duration.py` - End-to-end regression test generating 9s input, asserting ~5s output with exact frame count

## Decisions Made

- **Session-side cap over source pacing**: While FakeAudioModule could be paced to real-time, a session-side cap is more robust and works with any source type
- **Discard mode continues consumption**: After hitting max_frames, the consumer keeps reading frames but discards them. This prevents queue overflow and producer blocking during shutdown.
- **Exact frame assertion in test**: Rather than fuzzy duration matching, the test asserts exact frame count (seconds * sample_rate) for deterministic regression detection

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All verifications passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT Test 1 now passes (fake recording creates correct duration WAV)
- All 7 UAT tests pass (5 were already passing, 2 fixed by gap closure plans)
- Phase 1 Audio Capture Foundation is complete
- Ready to transition to Phase 2: Real-Time Transcription Engine

---
*Phase: 01-audio-capture-foundation*
*Completed: 2026-02-01*
