# T08: Implement clean application exit

**Slice:** S02 — **Milestone:** M001

## Description

Implement clean application exit: context menu with Exit, SIGINT handler for Ctrl+C, proper closeEvent, and close button on transcript panel.

**Purpose:** Current app has no clean exit path — right-click menu inaccessible, ALT+F4 closes widget but app continues, CTRL+C produces error, transcript panel has no close button.
**Output:** Multiple clean exit methods working correctly and widget position persistence.
