# WIDGET Requirement Traceability Matrix

Complete mapping of WIDGET-01 through WIDGET-32 requirements to test evidence and implementation status.

---

| Requirement | Description | Status | Test File | Test Function(s) | Notes |
|---|---|---|---|---|---|
| WIDGET-01 | Frameless, borderless circular window | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET01::test_frameless_window_hint` | Confirms `Qt.FramelessWindowHint` is set |
| WIDGET-02 | Always-on-top behavior | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET02::test_stays_on_top_hint` | Confirms `Qt.WindowStaysOnTopHint` is set |
| WIDGET-03 | Draggable via any point on widget | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET03::test_position_changes_after_drag` | Simulates mouse drag, verifies position delta |
| WIDGET-04 | Edge docking (snap to screen edge) | ✅ Validated | `test_widget_docking.py` | `TestSnapDetectionLeftRightOnly` (6 tests), `TestPeekPositionCalculation` (3 tests), `TestSlideAnimationInterpolation` (2 tests), `TestConfigPersistenceRoundTrip` (3 tests), `TestLiveMagnetSnapDuringDrag` (4 tests) | Left/right docking only — top/bottom removed per design decision (see MEM026) |
| WIDGET-05 | Peek mode when docked | ✅ Validated | `test_widget_docking.py` | `TestPeekPositionCalculation::test_peek_width_value`, `test_dock_left_peek_position`, `test_dock_right_peek_position` | Peek width = widget width × 0.2 |
| WIDGET-06 | Idle-state transparency | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET06::test_idle_opacity` | Verifies opacity < 1.0 in idle state |
| WIDGET-07 | Pulse animation during recording | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET07::test_pulse_formula_range`, `test_pulse_formula_values` | Validates pulse formula math |
| WIDGET-08 | Orbital animation system | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET08::test_four_orbit_entries`, `test_distinct_radii`, `test_distinct_speeds`, `test_required_keys` | 4 orbits with distinct radii and speeds |
| WIDGET-09 | Record button in scene | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET09::test_record_button_in_scene`, `test_record_button_type` | Confirms presence and type |
| WIDGET-10 | Three orbital members | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET10::test_three_members`, `test_expected_members` | Validates member count and identity |
| WIDGET-11 | Recording state visual | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET11_12::test_recording_state` | Visual state change on record start |
| WIDGET-12 | Idle state visual | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET11_12::test_idle_state` | Visual state reverts on record stop |
| WIDGET-13 | Mic and system audio lobes | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET13::test_mic_lobe_exists`, `test_system_lobe_exists`, `test_lobe_positions_differ` | Two lobes at distinct positions |
| WIDGET-14 | Mic source toggle | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET14_15::test_mic_lobe_toggles` | Toggles mic audio source on/off |
| WIDGET-15 | System audio toggle | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET14_15::test_system_lobe_toggles` | Toggles system audio source on/off |
| WIDGET-16 | Active/inactive lobe visual | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET16::test_locked_state`, `test_unlocked_state`, `test_active_inactive_visual` | Visual feedback per state |
| WIDGET-17 | Third lobe for transcript access | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET17::test_transcript_lobe_exists`, `test_transcript_lobe_in_scene`, `test_transcript_lobe_position_differs_from_others`, `test_transcript_lobe_toggles_panel_hide`, `test_transcript_lobe_toggles_panel_show` | Transcript lobe (document icon) at bottom-left toggles panel visibility |
| WIDGET-18 | Transcript flows from widget | ⚠️ Design Deviation | — | — | Separate `FloatingTranscriptPanel` QWidget docks adjacent to widget. See [WIDGET-DEVIATIONS.md](WIDGET-DEVIATIONS.md#widget-18-transcript-flows-from-widget) |
| WIDGET-19 | Recording state indicator | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET19::test_recording_state_transitions` | State machine transitions correctly |
| WIDGET-20 | Settings lobe visibility toggle | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET20::test_hides_when_visible`, `test_shows_when_hidden` | Toggles settings panel visibility |
| WIDGET-21 | Speaker labels in transcript | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET21::test_segment_with_speaker` | Speaker segment includes label |
| WIDGET-22 | Speaker color coding | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET22::test_multiple_entries`, `test_colors_distinct` | Distinct colors per speaker |
| WIDGET-23 | Sequential speaker numbering | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET23::test_sequential_keys` | Speakers numbered S1, S2, S3… |
| WIDGET-24 | Transcript panel speaker configuration | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET24::test_set_and_get` | Round-trip set/get of speaker config |
| WIDGET-25 | Auto-scroll during recording | ✅ Validated | `test_auto_scroll.py` | `TestProportionalThreshold` (4 tests), `TestPauseDetectionProportional` (3 tests), `TestIsAtBottomConsistent` (3 tests) | Proportional threshold, pause detection |
| WIDGET-26 | Pause on manual scroll-up | ✅ Validated | `test_auto_scroll.py` | `TestPauseDetectionProportional::test_scroll_well_above_bottom_triggers_pause`, `TestPauseTimerHidesBadge` (2 tests) | Auto-pause on scroll away from bottom |
| WIDGET-27 | New-content badge when paused | ✅ Validated | `test_auto_scroll.py` | `TestBadgeShowsOnPausedScroll` (2 tests), `TestBadgeIncrements` (2 tests), `TestBadgeClickResumes` (2 tests), `TestScrollToBottomResumes` (1 test), `TestBadgeHiddenWhenNotPaused` (2 tests) | Badge with count, click-to-resume |
| WIDGET-28 | Confidence indicator (high/medium/low) | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET28::test_high_green`, `test_medium_yellow`, `test_low_red`, `test_colors_distinct` | Three-tier color coding |
| WIDGET-29 | Enhanced segment bold styling | ⚠️ Design Deviation | — | — | Dual-mode enhanced bold removed in M001/S03 cleanup. Standard bold formatting used. See [WIDGET-DEVIATIONS.md](WIDGET-DEVIATIONS.md#widget-29-enhanced-segment-bold-styling) |
| WIDGET-30 | Legend overlay visibility toggle | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET30::test_hides_when_visible`, `test_shows_when_hidden` | Toggles legend overlay |
| WIDGET-31 | Widget context menu | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET31::test_context_menu_has_start_recording`, `test_context_menu_has_settings`, `test_context_menu_has_exit`, `test_context_menu_shows_stop_when_recording` | Implemented in T02: Start/Stop Recording, Settings, Exit |
| WIDGET-32 | System tray menu | ✅ Validated | `test_widget_requirements.py` | `TestWIDGET32::test_has_start_recording`, `test_has_hide_widget`, `test_has_exit`, `test_updates_to_stop_when_recording` | Tray menu with recording toggle |

---

## Summary

| Status | Count |
|---|---|
| ✅ Validated | 30 |
| ⚠️ Design Deviation | 2 |
| ❌ Failed | 0 |
| 🔲 Out of Scope | 0 |
| **Total** | **32** |

### Design Deviations (3)

All deviations are intentional and documented in [WIDGET-DEVIATIONS.md](WIDGET-DEVIATIONS.md):

1. **WIDGET-18** — Separate `FloatingTranscriptPanel` QWidget instead of integrated flow-out
2. **WIDGET-29** — Dual-mode enhanced bold removed; standard bold formatting sufficient

### Test Coverage Sources

| Test File | Requirements Covered |
|---|---|
| `tests/test_widget_requirements.py` | WIDGET-01–03, 06–16, 19–24, 28, 30–32 |
| `tests/test_widget_docking.py` | WIDGET-04, WIDGET-05 |
| `tests/test_auto_scroll.py` | WIDGET-25, WIDGET-26, WIDGET-27 |
| `tests/test_widget_visual_state.py` | Visual state machine (supports WIDGET-06/07/11/12/19) |
| `tests/test_theme.py` | Theme palette and CSS (supports WIDGET-06/22/28) |
| `tests/test_panel_resize.py` | Panel resize constraints (supports WIDGET-05/20/30) |
| `tests/test_audio_source_selection.py` | Audio source toggle (supports WIDGET-14/15) |

### Regression Suite Result

- **715 passed**, 9 skipped, 1 xfailed, 1 xpassed — zero failures
- Suite runtime: ~146 seconds
- Date: 2026-04-27
