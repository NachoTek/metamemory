# T06: Fix widget double-click requirement

**Slice:** S01 — **Milestone:** M001

## Description

Fix widget double-click requirement for record button and interactive lobes.

Purpose: All interactive items should respond to single clicks, not double clicks.
Root cause: Parent widget MeetAndReadWidget.mousePressEvent intercepts and accepts all left-button clicks, preventing child item handlers from executing.
Output: Click detection that distinguishes clicks from drags and allows events to propagate.
