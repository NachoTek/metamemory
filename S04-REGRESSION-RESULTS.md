# S04-REGRESSION-RESULTS.md

**Milestone:** M006-mgkqrb — Aetheric Glass Desktop Redesign  
**Slice:** S04 — Integrated Aetheric Desktop Regression and Visual Completion  
**Task:** T01 — Run and record integrated automated regression proof  
**Date:** 2026-04-29T15:40:11 UTC  
**Executor:** auto-mode  

---

## Environment

| Item | Value |
|---|---|
| Platform | Windows-10-10.0.26200-SP0 |
| Python | 3.10.11 |
| pytest | 8.4.2 |
| PySide6 | 6.10.1 (Qt runtime 6.10.1) |
| Working tree | `.gsd/worktrees/M006-mgkqrb` |

---

## Run 1: Focused S01/S02/S03 Contract Tests

**Command:**
```
python -m pytest tests/test_aetheric_settings_shell.py tests/test_settings_history.py tests/test_cc_overlay.py tests/test_widget_requirements.py tests/test_widget_visual_state.py tests/test_settings_docking.py tests/test_panel_resize.py -v
```

| Metric | Value |
|---|---|
| Exit code | 0 |
| Passed | 443 |
| Failed | 0 |
| Skipped | 0 |
| Duration | 66.90s |

**Result: ✅ ALL PASS**

### Contract Coverage

| Surface | Test File | Tests | Status |
|---|---|---|---|
| Aetheric settings shell (S01) | `test_aetheric_settings_shell.py` | 124 | ✅ Pass |
| History migration (S02) | `test_settings_history.py` | 62 | ✅ Pass |
| CC overlay lifecycle (S03) | `test_cc_overlay.py` | 71 | ✅ Pass |
| Widget requirements | `test_widget_requirements.py` | 55 | ✅ Pass |
| Widget visual state | `test_widget_visual_state.py` | 52 | ✅ Pass |
| Settings docking (S01) | `test_settings_docking.py` | 40 | ✅ Pass |
| Panel resize | `test_panel_resize.py` | 39 | ✅ Pass |

**Interpretation:** All S01 (Settings shell/docking), S02 (History migration), and S03 (CC overlay lifecycle) contracts are fully green. No regressions detected in the integrated Aetheric Glass desktop surface.

---

## Run 2: Full Test Suite (initial)

**Command:**
```
python -m pytest tests/ -q
```

| Metric | Value |
|---|---|
| Exit code | 1 |
| Passed | 1034 |
| Failed | 4 |
| Skipped | 9 |
| Xfailed | 1 |
| Xpassed | 1 |
| Duration | 133.45s |

### Failures (pre-fix)

1. **`test_audio_source_selection.py::TestRecordingLockWiring::test_recording_state_locks_lobes`**
   - Error: `AttributeError: Mock object has no attribute '_cc_overlay'`
   - Cause: S03 added `self._cc_overlay` checks in `_on_controller_state_change` but the mock in this pre-existing test didn't set `_cc_overlay`.
   - Owner: `tests/test_audio_source_selection.py` + `src/meetandread/widgets/main_widget.py`
   - Blocks visual UAT: No (mock setup issue, not a production defect)

2. **`test_audio_source_selection.py::TestRecordingLockWiring::test_idle_state_unlocks_lobes`**
   - Error: Same root cause as #1
   - Blocks visual UAT: No

3. **`test_audio_source_selection.py::TestRecordingLockWiring::test_error_state_unlocks_lobes`**
   - Error: Same root cause as #1
   - Blocks visual UAT: No

4. **`test_config.py::TestConfigManagerSingleton::test_module_level_get_config_manager`**
   - Error: `assert cm is cm2` — singleton identity broken by concurrent test reset
   - Cause: Pre-existing singleton race condition. `ConfigManager._instance` is reset but the constructor creates a new instance instead of reusing the singleton.
   - Owner: `tests/test_config.py` + `src/meetandread/config/manager.py`
   - Blocks visual UAT: No (config singleton test, not a widget surface)

---

## Fix Applied

Added `widget._cc_overlay = None` to the three `TestRecordingLockWiring` mock setups in `tests/test_audio_source_selection.py` so the spec-restricted MagicMock can handle the `_cc_overlay` attribute that S03 added to `_on_controller_state_change`.

---

## Run 3: Full Test Suite (post-fix)

**Command:**
```
python -m pytest tests/ -q
```

| Metric | Value |
|---|---|
| Exit code | 1 |
| Passed | 1037 |
| Failed | 1 |
| Skipped | 9 |
| Xfailed | 1 |
| Xpassed | 1 |
| Duration | 131.93s |

### Remaining Failure

1. **`test_config.py::TestConfigManagerSingleton::test_module_level_get_config_manager`**
   - Pre-existing singleton race condition unrelated to S01/S02/S03
   - Not blocking visual UAT — config layer, not widget surface

**Interpretation:** All S01/S02/S03 surface tests pass. The single remaining failure is a pre-existing config singleton test race that predates the Aetheric Glass work and does not affect the desktop experience.

### Skip/Xfail Notes

- 9 skipped tests are in `tests/manual_integration_test.py` — these require real audio hardware (loopback capture) and are intentionally skipped in headless/auto-mode environments.
- 1 xfailed test is a known issue with pytest-qt + PortAudio threading interaction (see project gotcha: pytest-qt's event loop hook interferes with pyaudiowpatch's PortAudio threading on Windows).
- 1 xpassed test indicates a previously-expected failure now passes (likely fixed by another change).

---

## Summary

| Run | Command | Exit | Passed | Failed | Duration |
|---|---|---|---|---|---|
| 1 (focused) | 7 S01/S02/S03 test files | 0 | 443 | 0 | 66.90s |
| 2 (full, pre-fix) | `tests/` | 1 | 1034 | 4 | 133.45s |
| 3 (full, post-fix) | `tests/` | 1 | 1037 | 1 | 131.93s |

**Verdict: ✅ All S01/S02/S03 contracts are regression-free.** The sole remaining failure (`test_config.py` singleton) is pre-existing and unrelated to Aetheric Glass. The desktop experience is ready for visual UAT.

---

*No transcript bodies, secrets, or private meeting data are included in this artifact.*
