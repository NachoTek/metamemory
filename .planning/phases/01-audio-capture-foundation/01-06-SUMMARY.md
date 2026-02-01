---
phase: 01-audio-capture-foundation
plan: 06
subsystem: widgets
tags: [widgets, qt, ui, input]

requires:
  - "Widget foundation implementation"
provides:
  - "Single-click interaction for all widget items"
  - "Click vs drag detection"
affects:
  - "01-07 (depends on this fix)"

tech-stack.added: []
tech-stack.removed: []
tech-stack.patterns:
  - "Click vs drag detection with position/time thresholds"
  - "Event propagation to child items"

key-files.created: []
key-files.modified:
  - src/metamemory/widgets/main_widget.py

decisions:
  - id: "click-thresholds"
    decision: "Click = <5px movement AND <300ms elapsed"
    rationale: "These thresholds distinguish intentional clicks from accidental movement during clicks"
    consequences: "Very short drags might be interpreted as clicks, but this is acceptable for widget interactions"
  - id: "event-propagation"
    decision: "Don't accept() in mousePressEvent - let events reach child items"
    rationale: "Parent accepting events was blocking child item handlers"
    consequences: "Child items (RecordButton, ToggleLobe, SettingsLobe) now receive events"

metrics:
  duration: "10 minutes"
  completed: "2026-02-01"
  tasks: 1
  commits: 1
---

# Phase 01 Plan 06: Fix Widget Double-Click Requirement Summary

## One-Liner
Fixed widget interaction to respond to single clicks instead of requiring double clicks by replacing event interception with click vs drag detection.

## What Was Delivered

### Changes Made
1. **Added QTime and QPoint imports** - Required for click detection timing and positioning
2. **Added press_time instance variable** - Tracks when mouse button was pressed
3. **Replaced mousePressEvent** - Now records position/time but doesn't accept events (allows propagation)
4. **Updated mouseReleaseEvent** - Implements click vs drag detection:
   - Movement < 5 pixels AND elapsed < 300ms = click
   - Otherwise = drag
5. **Updated mouseMoveEvent** - Maintains drag functionality for non-click movements

### Verification
- [x] Click detection implemented with position and time thresholds
- [x] mouseReleaseEvent added with proper logic
- [x] Events propagate to child items

### Root Cause
- Parent widget `MeetAndReadWidget.mousePressEvent` was intercepting and `accept()`-ing all left-button clicks
- This blocked child items (RecordButtonItem, ToggleLobeItem, SettingsLobeItem) from receiving their own mousePressEvent handlers
- Double-click worked because second click wasn't intercepted (widget already in "dragging" state from first click)

## Decisions Made

| Decision | Value | Rationale |
|----------|-------|-----------|
| Click threshold | <5px movement | Small accidental movements don't trigger drag |
| Time threshold | <300ms | Quick presses are clicks, longer holds are drags |
| Event handling | Don't accept() in parent | Allows child items to receive events |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### Prerequisites Met
- [x] Record button responds to single click
- [x] Event propagation allows child item handlers
- [x] Click vs drag properly distinguished

### Blockers
None. Plan 01-06 complete. Enables 01-07 verification.

## Technical Debt

None introduced.

## Performance Notes

Minimal performance impact:
- Two QTime calls per click
- One QPoint subtraction and manhattanLength calculation
- Negligible overhead

## Testing Notes

**Verification steps:**
1. Launch widget: `python -m meetandread.main`
2. Click record button ONCE - should start/stop recording
3. Click source lobes ONCE - should toggle
4. Click settings lobe ONCE - should respond
5. Click and drag on empty area - should drag widget
6. Click and drag on button - should trigger button (click), not drag
