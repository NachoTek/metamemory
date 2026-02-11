---
status: resolved
trigger: "Clicking settings lobe crashes app with AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'"
created: "2026-02-06T00:00:00Z"
updated: "2026-02-06T00:00:00Z"
---

## Current Focus

hypothesis: FloatingSettingsPanel is missing the dock_to_widget method that FloatingTranscriptPanel has
test: Compare both class implementations in floating_panels.py
expecting: Confirm FloatingSettingsPanel is missing the method
next_action: Document findings and provide fix

## Symptoms

expected: Settings panel should dock to main widget when toggled
actual: App crashes with AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'
errors: AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'
reproduction: Click settings button in main widget to toggle settings panel
started: Phase 2 UAT

## Evidence

- timestamp: 2026-02-06T00:00:00Z
  checked: src/metamemory/widgets/main_widget.py line 525
  found: Code calls self._floating_settings_panel.dock_to_widget(self, "right")
  implication: This is the call site causing the crash

- timestamp: 2026-02-06T00:00:00Z
  checked: src/metamemory/widgets/floating_panels.py FloatingTranscriptPanel class (lines 23-299)
  found: Has dock_to_widget method at lines 118-144
  implication: This is the expected implementation pattern

- timestamp: 2026-02-06T00:00:00Z
  checked: src/metamemory/widgets/floating_panels.py FloatingSettingsPanel class (lines 302-420)
  found: Does NOT have dock_to_widget method - only has __init__, show_panel, hide_panel, closeEvent, mouse events
  implication: This is the root cause - method was not implemented

## Resolution

root cause: FloatingSettingsPanel class was created as a copy of the pattern from FloatingTranscriptPanel, but the dock_to_widget method was omitted during implementation. The main_widget.py code at line 525 calls this method, but it doesn't exist in FloatingSettingsPanel.

fix: Add the dock_to_widget method to FloatingSettingsPanel class, copying the implementation from FloatingTranscriptPanel (lines 118-144).

verification: Settings panel should dock to right side of main widget when clicked, without crashing.

files_changed:
  - src/metamemory/widgets/floating_panels.py: Add dock_to_widget method to FloatingSettingsPanel class
