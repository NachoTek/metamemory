# S01: Audio Capture Foundation

**Goal:** Implement crash-safe on-disk recording primitives (paths + streaming writer + WAV finalizer + recovery).
**Demo:** Implement crash-safe on-disk recording primitives (paths + streaming writer + WAV finalizer + recovery).

## Must-Haves


## Tasks

- [x] **T01: Crash-safe audio storage**
  - Implement crash-safe on-disk recording primitives (paths + streaming writer + WAV finalizer + recovery).

Purpose: Make audio durable (AUD-07) before wiring real capture.
Output: Storage modules + automated tests proving a recovered WAV is playable.
- [x] **T02: WASAPI capture backends**
  - Add WASAPI capture backends (mic + system loopback) and a FakeAudioSource, with device enumeration utilities.

Purpose: Establish reliable capture primitives (AUD-01, AUD-02, AUD-06, AUD-08 foundation) before session wiring.
Output: Capture modules + dependency updates.
- [x] **T03: Session wiring**
  - Implement a recording session manager that can consume mic/system/fake sources, resample/mix to 16kHz mono, stream to disk, and finalize to WAV.

Purpose: Deliver the core "start -> stream -> stop -> playable WAV" pipeline (AUD-04, AUD-05, AUD-07, and foundations for AUD-01/02/03/08).
Output: Session module + CLI harness + automated end-to-end tests using FakeAudioModule.
- [x] **T04: Widget integration**
  - Wire the widget UI to the recording pipeline, add startup recovery UX, and verify real device capture quality and long-run stability.

Purpose: Complete Phase 1 user-facing flow and validate against success criteria.
Output: Working widget-driven recording (mic/system/both) + recovery prompt + manual verification checklist.
- [x] **T05: Fix FakeAudioModule endless looping**
  - Fix FakeAudioModule endless looping issue to create WAVs of specified duration.

Purpose: Fake recordings must terminate naturally after N seconds, not loop indefinitely.
Root cause: Hardcoded loop=True + race condition (drain competes with source read thread).
Output: Fixed fake recordings that create N-second WAVs cleanly.
- [x] **T06: Fix widget double-click requirement**
  - Fix widget double-click requirement for record button and interactive lobes.

Purpose: All interactive items should respond to single clicks, not double clicks.
Root cause: Parent widget MeetAndReadWidget.mousePressEvent intercepts and accepts all left-button clicks, preventing child item handlers from executing.
Output: Click detection that distinguishes clicks from drags and allows events to propagate.
- [x] **T07: Verify widget lobes single-click**
  - Verify Gap 3 fix - Widget lobes single-click functionality.

Purpose: This gap has the same root cause as Gap 2 (parent widget event.accept() blocking events) and is already fixed by plan 01-06.
Root cause: Same parent event handling issue - resolved in plan 01-06.
Output: Verification that lobes respond to single click after 01-06 fix.
- [x] **T08: Fix crash recovery false positive**
  - Fix crash recovery false positive by cleaning up .pcm.part files after successful finalization.

Purpose: Recovery should only prompt when there are actual crash leftovers, not on every startup.
Root cause: finalize_stem() called with default delete_part=False, leaving .pcm.part files after successful WAV creation. On next startup, has_partial_recordings() detects these as crash leftovers.
Output: Clean recordings directory after normal shutdown, no false positive prompts.
- [x] **T09: Fix CLI fake recording duration**
  - Fix the CLI fake recording duration so `--seconds N` produces an ~N second WAV even when the fake source can emit audio faster than real-time.

Purpose: UAT expects `python -m metamemory.audio.cli record --fake <wav> --seconds 5` to yield an output WAV ~5 seconds long; currently it can produce a 1:1 copy of the full input file.
Output: Session-level frame cap wired from CLI + regression test.
- [x] **T10: Fix widget drag and click-through**
  - Fix widget drag and click-through by adding a hit-testable background drag surface and restoring the drag-start transition.

Purpose: UAT expects the widget can be dragged from empty/non-interactive areas; currently there is no hit-testable empty area (click-through) and dragging never starts because `is_dragging` is never set True.
Output: Drag surface + correct click-vs-drag state machine.

## Files Likely Touched

