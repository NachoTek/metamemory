---
status: diagnosed
trigger: "Diagnose Issue #1 from Phase 2 UAT: AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'"
created: 2026-02-10T00:00:00.000Z
updated: 2026-02-10T00:00:00.000Z
---

## Current Focus
hypothesis: The AttributeError reported is UNLIKELY in current codebase (dock_to_widget exists since commit c53a564). The REAL issue is: Settings panel UI does not display hardware specs or recommended model indicator.

test:
  1. Confirm dock_to_widget method exists (✓ confirmed at line 474)
  2. Check if settings panel has hardware display code (✗ NOT found in __init__)
expecting: dock_to_widget exists and works, but settings panel needs hardware detection UI integration
next_action: Prepare diagnostic summary for fix planning - missing hardware detection in settings panel UI

## Symptoms
expected: Settings panel should show:
  - Hardware specs (RAM, CPU cores, frequency)
  - Model recommendation (tiny/base/small)
expected: Clicking settings lobe should open panel without errors
actual: 
  - Reported: "Clicking settings lobe crashes app: AttributeError: 'FloatingSettingsPanel' object has no attribute 'dock_to_widget'"
  - Console shows: Hardware detection worked (RAM: 63.4 GB, CPU: 12 cores, Recommended model: tiny)
  - After fix: Shows models (Tiny/Base/Small) with Tiny as default, BUT MISSING system specs and recommended model indicator
errors: AttributeError (if dock_to_widget truly doesn't exist in user's version)
missing: System specs and recommended model indicator in settings panel UI
reproduction: Click settings lobe to open settings panel
started: Phase 2 UAT Test 2 (Hardware Detection Display)

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence

- timestamp: 2026-02-10T00:00:00Z
  checked: src/metamemory/widgets/floating_panels.py lines 474-500
  found: FloatingSettingsPanel.dock_to_widget() method EXISTS at line 474
  implication: Method is present in current code, AttributeError should not occur

- timestamp: 2026-02-10T00:00:00Z
  checked: src/metamemory/widgets/main_widget.py line 546
  found: Code calls self._floating_settings_panel.dock_to_widget(self, "right")
  implication: This call is expected to work if dock_to_widget exists

- timestamp: 2026-02-10T00:00:00Z
  checked: Git history commit c53a564
  found: commit "fix(02-06): add dock_to_widget method to FloatingSettingsPanel" (Feb 6, 2026)
  implication: This commit was supposed to add the method and fix the crash

- timestamp: 2026-02-10T00:00:00Z
  checked: Git merge-base c53a564..HEAD
  found: c53a564 IS an ancestor of current HEAD (main branch)
  implication: The fix should be present in all commits after c53a564

- timestamp: 2026-02-10T00:00:00Z
  checked: Git commits between c53a564 and HEAD that modified floating_panels.py
  found: fab3877 (add close button) and 6d13582 (auto-scroll pause)
  implication: No commit has removed dock_to_widget from FloatingSettingsPanel

- timestamp: 2026-02-10T00:00:00Z
  checked: src/metamemory/widgets/floating_panels.py lines 384-462 (FloatingSettingsPanel.__init__)
  found: Settings panel __init__ only has window settings, style, title, model selection, close button
  implication: NO code to display hardware specs or recommended model indicator
  missing: Hardware detection integration code in UI

- timestamp: 2026-02-10T00:00:00Z
  checked: src/metamemory/hardware/recommender.py
  found: ModelRecommender class with get_detected_specs() and get_recommendation() methods
  implication: Hardware detection infrastructure exists and works (confirmed by console output in issue)

- timestamp: 2026-02-10T00:00:00Z
  checked: .planning/debug/resolved/settings-panel-dock-method-missing.md
  found: Previous diagnostic session found missing dock_to_widget method (resolved in commit c53a564)
  implication: The AttributeError issue was already diagnosed and fixed

- timestamp: 2026-02-10T00:00:00Z
  checked: Git merge-base c53a564..HEAD
  found: c53a564 IS an ancestor of current HEAD (main branch)
  implication: The fix should be present in all commits after c53a564

- timestamp: 2026-02-10T00:00:00Z
  checked: Git commits between c53a564 and HEAD that modified floating_panels.py
  found: fab3877 (add close button) and 6d13582 (auto-scroll pause)
  implication: No commit has removed dock_to_widget from FloatingSettingsPanel

- timestamp: 2026-02-10T00:00:00Z
  checked: src/metamemory/widgets/floating_panels.py lines 384-462 (FloatingSettingsPanel.__init__)
  found: Settings panel __init__ only has:
    - Window flags and size (lines 388-395)
    - CSS style sheet (lines 398-422)
    - Vertical layout with title "Settings" (line 430)
    - Model selection section with QRadioButton buttons (lines 435-450)
    - Close button (lines 455-458)
  implication: NO code to display hardware specs (RAM, CPU) or recommended model indicator
  missing: Hardware detection integration code in UI

- timestamp: 2026-02-10T00:00:00Z
  checked: UAT issue report and phase plan 02-06
  found: UAT Test 2 expected settings panel to show hardware detection (RAM, CPU, recommended model)
  implication: Missing feature: integrate hardware detection into settings panel UI

## Resolution

**ROOT CAUSE FOUND: MISDIAGNOSED ISSUE**

The AttributeError reported in the UAT issue is **UNLIKELY to occur** in the current codebase. The REAL issue is that the settings panel UI does not display hardware detection information.

### Issue 1: AttributeError (LIKELY FALSE ALARM)
**Status: FIXED in current codebase**

**Evidence:**
- ✓ dock_to_widget method EXISTS at line 474 in `src/metamemory/widgets/floating_panels.py`
- ✓ Added in commit c53a564: "fix(02-06): add dock_to_widget method to FloatingSettingsPanel"
- ✓ Current code has TWO dock_to_widget methods (TranscriptPanel: line 159, SettingsPanel: line 474)
- ✓ c53a564 is an ancestor of current HEAD (main branch)
- ✓ No subsequent commits have removed dock_to_widget

**Conclusion:** If a user reports AttributeError, they are likely using an older version before commit c53a564.

### Issue 2: Missing Hardware Display in Settings Panel (REAL ISSUE)
**Status: NOT IMPLEMENTED**

**Expected Behavior:**
Settings panel should show:
- Detected RAM (e.g., "RAM: 63.4 GB")
- CPU cores (e.g., "CPU: 12 cores")
- Frequency (e.g., "2.4 GHz")
- Recommended model indicator (e.g., "Recommended: tiny")

**Actual Behavior:**
Settings panel only shows "Model Size:" with radio buttons (Tiny/Base/Small)

**Root Cause:**
`FloatingSettingsPanel.__init__()` at lines 384-462 has NO code to integrate hardware detection

**Evidence:**
- Read entire `__init__` method (lines 384-462)
- Only contains: window flags, size, style sheet, title, model selection buttons, close button
- No imports from `metamemory.hardware.*` (detector, recommender)
- No calls to `ModelRecommender` to get hardware specs
- No QLabel widgets to display RAM, CPU, or recommended model

### Suggested Fix

**File:** `src/metamemory/widgets/floating_panels.py`

**Location:** Add hardware display section in `FloatingSettingsPanel.__init__()` between title (line 432) and model selection (line 435)

**Implementation Steps:**

1. **Add imports at top of file** (already present, but verify):
   ```python
   from metamemory.hardware.detector import HardwareDetector
   from metamemory.hardware.recommender import ModelRecommender
   ```

2. **Add hardware display section in __init__** (after line 432):
   ```python
   # Hardware detection section
   try:
       from metamemory.hardware.recommender import ModelRecommender
       recommender = ModelRecommender()
       specs = recommender.get_detected_specs()
       rec_model = recommender.get_recommendation()

       # Hardware specs label
       from PyQt6.QtWidgets import QLabel
       from PyQt6.QtGui import QFont

       hw_label = QLabel(f"System Specs:\n  RAM: {specs.total_ram_gb:.1f} GB\n  CPU: {specs.cpu_count_logical} cores\n  Recommended: {rec_model}")
       hw_label.setStyleSheet("""
           QLabel {
               color: #aaa;
               font-size: 11px;
               padding: 5px;
               background-color: #252525;
               border-radius: 5px;
           }
       """)
       layout.addWidget(hw_label)

       # Model recommendation highlight
       rec_label = QLabel(f"Recommended: {rec_model.upper()}")
       rec_label.setStyleSheet("""
           QLabel {
               color: #4CAF50;
               font-weight: bold;
               font-size: 12px;
               padding: 3px;
           }
       """)
       layout.addWidget(rec_label)

   except Exception as e:
       # Log error but don't crash UI
       import logging
       logging.getLogger(__name__).error(f"Failed to load hardware info: {e}")
   ```

3. **Test:**
   - Click settings lobe
   - Verify panel displays: "System Specs: RAM: 63.4 GB, CPU: 12 cores, Recommended: tiny"
   - Verify model radio buttons still work

### Verification Criteria
- [ ] Settings panel shows RAM, CPU, and recommended model
- [ ] Hardware info loads without errors
- [ ] Model selection still functions normally
- [ ] Panel docks correctly to widget edge
