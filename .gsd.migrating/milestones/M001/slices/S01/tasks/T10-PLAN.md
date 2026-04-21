# T10: Fix widget drag and click-through

**Slice:** S01 — **Milestone:** M001

## Description

Fix widget drag and click-through by adding a hit-testable background drag surface and restoring the drag-start transition.

Purpose: UAT expects the widget can be dragged from empty/non-interactive areas; currently there is no hit-testable empty area (click-through) and dragging never starts because `is_dragging` is never set True.
Output: Drag surface + correct click-vs-drag state machine.
