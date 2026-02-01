---
phase: 01-audio-capture-foundation
plan: 10
subsystem: ui

tags: [widget, qt6, pyqt6, drag-drop, hit-testing, borderless]

# Dependency graph
requires:
  - phase: 01-audio-capture-foundation
    provides: Widget base implementation from 01-04
provides:
  - Invisible drag surface covering entire widget for hit-testing
  - Click vs drag state machine with movement threshold
  - Prevention of click-through to underlying applications
  - Drag initiation from empty widget areas
affects:
  - Phase 5 Widget Interface
  - All widget interaction UX

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Invisible hit-testable background surface with alpha=1"
    - "Scene-level item detection for drag surface identification"
    - "Click vs drag threshold: < 5px movement = click"

key-files:
  created: []
  modified:
    - src/metamemory/widgets/main_widget.py - Added DragSurfaceItem class, integrated into widget

key-decisions:
  - "Drag surface must have alpha=1 (not 0) to be hit-testable in Qt"
  - "Z-value -1000 keeps drag surface behind all interactive controls"
  - "Movement threshold of 5px balances accidental drags vs intended clicks"

patterns-established:
  - "DragSurfaceItem: Near-transparent rectangle covering entire scene, z=-1000"
  - "Press tracking: Store whether press started on drag surface in mousePressEvent"
  - "Click vs drag: Use manhattanLength() threshold of 5px"

# Metrics
duration: 12min
completed: 2026-02-01
---

# Phase 1 Plan 10: Widget Drag Surface Summary

**Invisible drag surface that enables dragging from empty widget areas and prevents click-through, with fixed click vs drag state machine**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-01T22:54:00Z
- **Completed:** 2026-02-01T23:06:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created `DragSurfaceItem` class as invisible hit-testable background surface
- Drag surface covers entire widget scene with alpha=1 (near-invisible but hit-testable)
- Z-value of -1000 ensures drag surface stays behind all interactive controls
- Modified mouse event handling to track `_press_on_drag_surface` state
- Fixed drag state machine to properly distinguish click from drag using 5px threshold
- Widget can now be dragged from empty areas (not just record button)
- Click-through to underlying applications prevented
- Buttons and lobes remain fully functional with single click
- Snap-to-edge behavior preserved and functional

## Task Commits

Each task was committed atomically:

1. **Task 1: Add drag surface item** - `898bf7c` (feat)
2. **Task 2: Fix drag state machine** - `89b9a11` (fix)

**Plan metadata:** (to be committed after SUMMARY)

## Files Created/Modified

- `src/metamemory/widgets/main_widget.py` - Added DragSurfaceItem class with near-transparent hit-testing surface; integrated into widget initialization; fixed mouse event handling for click vs drag detection

## Decisions Made

- **Alpha=1 for hit-testability**: Qt requires non-zero alpha for hit-testing. Alpha=1 is effectively invisible but enables mouse event capture.
- **Z-value -1000 positioning**: Negative z-value places drag surface behind all interactive components (record button, lobes) which have default z=0.
- **5px movement threshold**: Balances preventing accidental drags during clicks with allowing intentional drags to start smoothly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. User verification confirmed all functionality works correctly:
- Widget can be dragged from empty areas
- No click-through to underlying applications
- Buttons and lobes work with single click
- Snap-to-edge behavior intact

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 7 UAT tests pass
- Phase 1 Audio Capture Foundation is complete (10 of 10 plans)
- Widget interaction fully functional for user testing
- Ready to transition to Phase 2: Real-Time Transcription Engine

---
*Phase: 01-audio-capture-foundation*
*Completed: 2026-02-01*
