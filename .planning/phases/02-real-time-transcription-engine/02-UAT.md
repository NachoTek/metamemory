---
status: diagnosed
phase: 02-real-time-transcription-engine
source: 
  - 02-01-SUMMARY.md
  - 02-02-SUMMARY.md
  - 02-03-SUMMARY.md
  - 02-04-SUMMARY.md
  - 02-05-SUMMARY.md
  - BUGFIX-dedup-silence-SUMMARY.md
started: 2026-02-05T00:00:00Z
updated: 2026-02-05T00:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Application Launch Without Errors
expected: Run `python -m metamemory`. Application window appears without WinError 1114 or DLL errors. Widget displays with record button and audio source lobes.
result: pass

### 2. Hardware Detection Display
expected: Settings panel shows detected hardware (RAM, CPU cores, frequency) with model recommendation (tiny/base/small) based on your system specs.
result: issue
reported: "Clicking settings lobe crashes app: AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'. Console shows hardware detection worked (RAM: 63.4 GB, CPU: 12 cores, Recommended model: tiny) but settings panel cannot be opened."
severity: blocker

### 3. Model Selection Persistence
expected: Change model size in settings (e.g., tiny → base). Close and restart application. Reopen settings - selected model persists.
result: skipped
reason: "Blocked by Test 2 failure - settings panel cannot be opened due to dock_to_widget AttributeError"

### 4. Transcription Starts Within 2 Seconds
expected: Click record button. Start speaking. Transcript text appears in panel within 2 seconds of speech.
result: pass

### 5. Confidence Color Coding
expected: As words appear, they show color-coded confidence - green (high 80-100%), yellow (medium 70-80%), orange (low 50-70%), red (very low 0-50%).
result: pass
notes: "Works at line level (not individual words). User requests word-level coloring as future enhancement post-release."

### 6. No Duplicate Lines After Silence
expected: Speak, pause for 3+ seconds (silence), speak again. New speech appears on a new line without duplicating the previous line.
result: pass

### 7. Continuous Transcription Without Lag
expected: Record continuously for 2-3 minutes while speaking. Transcription keeps pace with speech without accumulating delay.
result: pass

### 8. Transcript Auto-Scroll
expected: While recording, transcript panel auto-scrolls to show latest words. Scrolling up manually pauses auto-scroll for ~10 seconds.
result: issue
reported: "Auto-scroll works (always shows bottom) but when scrolling up manually, it immediately fights to scroll back down instead of pausing. Manual scroll pause feature is not working."
severity: major

### 9. Transcript File Saved
expected: Stop recording. Check recording directory (shown in console or config). File `transcript-{timestamp}.md` exists with timestamps and text.
result: issue
reported: "File exists but contents are incorrect. System outputs entire whisper model result each pass instead of only new content, causing repeating text that accumulates. Example: 'Testing one two. Testing one two testing. Hello, this is a test of Testing one two testing...' - text keeps repeating and growing as audio buffer replays through model."
severity: blocker

### 10. Widget Dock and Position Persistence
expected: Drag widget to screen edge - it docks showing 4/5ths. Move to new position. Close and restart - widget returns to last position.
result: issue
reported: "Cannot test position persistence - no clean exit available. Right-click menu inaccessible, ALT+F4 closes widget but app continues running, must use CTRL+C which produces KeyboardInterrupt error. Transcript panel has no close button or lobe as intended."
severity: major

## Summary

total: 10
passed: 5
issues: 4
pending: 0
skipped: 1

## Gaps

- truth: "Settings panel opens when clicking settings lobe"
  status: failed
  reason: "User reported: Clicking settings lobe crashes app: AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'. Console shows hardware detection worked (RAM: 63.4 GB, CPU: 12 cores, Recommended model: tiny) but settings panel cannot be opened."
  severity: blocker
  test: 2
  root_cause: "FloatingSettingsPanel class is missing the dock_to_widget method that exists in FloatingTranscriptPanel. When settings button is clicked, main_widget.py line 525 attempts to call dock_to_widget() but this method was never implemented in FloatingSettingsPanel."
  artifacts:
    - path: "src/metamemory/widgets/main_widget.py"
      issue: "Line 525 calls dock_to_widget() on settings panel"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Lines 302-420 - FloatingSettingsPanel missing dock_to_widget method"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Lines 118-144 - FloatingTranscriptPanel has working implementation (reference)"
  missing:
    - "Add dock_to_widget method to FloatingSettingsPanel class"
  debug_session: ".planning/debug/resolved/settings-panel-dock-method-missing.md"
- truth: "Manual scroll pauses auto-scroll for ~10 seconds"
  status: failed
  reason: "User reported: Auto-scroll works (always shows bottom) but when scrolling up manually, it immediately fights to scroll back down instead of pausing. Manual scroll pause feature is not working."
  severity: major
  test: 8
  root_cause: "FloatingTranscriptPanel has completely missing user scroll detection and pause mechanism. No connection to verticalScrollBar().valueChanged signal, no pause state flag, no pause timer. The scroll_timer unconditionally scrolls to bottom every 100ms and _scroll_to_bottom() unconditionally sets scrollbar to maximum, overriding any manual scroll."
  artifacts:
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Line 151 - scroll_timer unconditionally scrolls every 100ms"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Line 220 - _scroll_to_bottom() called on every transcript update"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Lines 262-265 - _scroll_to_bottom() unconditionally sets scrollbar to maximum"
  missing:
    - "Connection to verticalScrollBar().valueChanged signal"
    - "Pause state flag (_auto_scroll_paused)"
    - "Pause timer (QTimer) to auto-resume after 10 seconds"
    - "Smart scroll logic that respects pause state"
  debug_session: ".planning/debug/autoscroll-pause-issue.md"
- truth: "Transcript file contains accurate text without repetition"
  status: failed
  reason: "User reported: File exists but contents are incorrect. System outputs entire whisper model result each pass instead of only new content, causing repeating text that accumulates. Example: 'Testing one two. Testing one two testing. Hello, this is a test of Testing one two testing...' - text keeps repeating and growing as audio buffer replays through model."
  severity: blocker
  test: 9
  root_cause: "AccumulatingTranscriptionProcessor re-transcribes entire accumulated audio buffer on every update cycle (every 2 seconds), and ALL resulting segments are added to the transcript store. The _phrase_bytes buffer accumulates continuously, is only cleared after 3 seconds of silence, and each transcription outputs full accumulated text. No deduplication tracks which segments were already output."
  artifacts:
    - path: "src/metamemory/transcription/accumulating_processor.py"
      issue: "Line 227 - Buffer accumulates: self._phrase_bytes += chunk_bytes"
    - path: "src/metamemory/transcription/accumulating_processor.py"
      issue: "Lines 279-283 - Triggers transcription every 2s without clearing buffer"
    - path: "src/metamemory/transcription/accumulating_processor.py"
      issue: "Line 341 - Transcribes entire buffer each time"
    - path: "src/metamemory/transcription/accumulating_processor.py"
      issue: "Lines 346-379 - Outputs ALL segments every cycle"
    - path: "src/metamemory/recording/controller.py"
      issue: "Lines 380-392 - Adds all words from every segment result"
  missing:
    - "Track last segment index to only emit new/changed segments"
    - "Deduplication to prevent adding same text multiple times"
  debug_session: ".planning/debug/transcript-repetition-issue.md"
- truth: "Application can be cleanly exited and position persists"
  status: failed
  reason: "User reported: Cannot test position persistence - no clean exit available. Right-click menu inaccessible, ALT+F4 closes widget but app continues running, must use CTRL+C which produces KeyboardInterrupt error. Transcript panel has no close button or lobe as intended."
  severity: major
  test: 10
  root_cause: "Four separate issues: (1) No context menu implementation in MeetAndReadWidget - no contextMenuPolicy, QMenu, or event handler. (2) No closeEvent() override to trigger application quit, plus Tool window flag prevents normal close behavior. (3) No SIGINT handler for Ctrl+C. (4) FloatingTranscriptPanel lacks close button/lobe that FloatingSettingsPanel has."
  artifacts:
    - path: "src/metamemory/widgets/main_widget.py"
      issue: "Lines 76-144 - No context menu implementation"
    - path: "src/metamemory/widgets/main_widget.py"
      issue: "Lines 80-84 - Tool window flag, no closeEvent() override"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Lines 62-104 - FloatingTranscriptPanel has no close button"
    - path: "src/metamemory/widgets/floating_panels.py"
      issue: "Lines 348-382 - FloatingSettingsPanel has close button (reference)"
    - path: "src/metamemory/main.py"
      issue: "Lines 157-204 - No SIGINT handler"
  missing:
    - "Context menu with Exit action"
    - "closeEvent() override that calls QApplication.quit()"
    - "SIGINT signal handler for graceful Ctrl+C"
    - "Close button on FloatingTranscriptPanel"
  debug_session: ".planning/debug/clean-exit-issues.md"
