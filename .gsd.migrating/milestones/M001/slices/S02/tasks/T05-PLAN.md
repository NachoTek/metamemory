# T05: Fix settings panel dock_to_widget crash

**Slice:** S02 — **Milestone:** M001

## Description

Fix the AttributeError crash when opening settings panel by adding the missing `dock_to_widget` method to `FloatingSettingsPanel`.

**Purpose:** Unblock the settings functionality which is currently unreachable due to a crash.
**Output:** Working `dock_to_widget` method in `FloatingSettingsPanel` that allows settings panel to dock to widget edges.
