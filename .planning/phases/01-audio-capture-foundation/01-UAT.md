- truth: "CLI fake recording should create WAV of specified duration (e.g., 5 seconds)"
  status: failed
  reason: "User reported: Recording generated 3 hours 2 min 53 sec instead of expected 5 seconds. Test file was 7 seconds long but FakeAudioModule kept looping it repeatedly. No progress shown either."
  severity: major
  test: 2
  root_cause: "FakeAudioModule is created with hardcoded loop=True parameter (session.py:367), causing fake audio source to continuously loop to file indefinitely. Combined with a race condition where drain loop consumes frames while source's read thread is still adding them (sources stopped AFTER drain), this leads to extended recording duration."
  artifacts:
    - path: "src/metamemory/audio/session.py:367"
      issue: "Hardcoded loop=True prevents natural termination - fake source generates frames infinitely"
      suggested_fix: "Add loop parameter to SourceConfig and use it instead of hardcoded True"
    - path: "src/metamemory/audio/session.py:290-315"
      issue: "Sources stopped AFTER drain loop, causing race condition where drain competes with source's read thread"
      suggested_fix: "Stop sources before running drain loop to prevent new frames being added during stop()"
    - path: "src/metamemory/audio/cli.py:158"
      issue: "No way to specify loop behavior when using --fake flag"
      suggested_fix: "Add loop parameter to SourceConfig call and set loop=False for fake recordings"
  missing:
    - "loop parameter in SourceConfig dataclass (session.py:78-90)"
    - "CLI argument or default behavior to set loop=False for fake audio sources"
    - "Drain loop timeout mechanism to prevent excessive frame processing during stop()"
  debug_session: ".planning/debug/fake-audio-looping.md"
- truth: "Widget record button should respond to single click to start/stop recording"
  status: failed
  reason: "User reported: Button state change requires double click when it should require single click."
  severity: major
  test: 5
  root_cause: "Parent widget MeetAndReadWidget.mousePressEvent (lines 147-161) intercepts and accepts all left-button clicks on RecordButtonItem/ToggleLobeItem/SettingsLobeItem, preventing these items' own mousePressEvent handlers from executing. Items have correct click handlers that never get called because event.accept() stops propagation before events reach them."
  artifacts:
    - path: "src/metamemory/widgets/main_widget.py:147-161"
      issue: "Parent widget consumes click events before items can handle them"
      suggested_fix: "Don't accept events on interactive items - use mouseReleaseEvent with position threshold to distinguish click vs drag"
    - path: "src/metamemory/widgets/main_widget.py:426-430"
      issue: "RecordButtonItem.mousePressEvent never executed (blocked by parent)"
      suggested_fix: "Events must propagate to this handler for single-click to work"
    - path: "src/metamemory/widgets/main_widget.py:481-487"
      issue: "ToggleLobeItem.mousePressEvent never executed (blocked by parent)"
      suggested_fix: "Events must propagate to this handler for single-click to work"
    - path: "src/metamemory/widgets/main_widget.py:514-518"
      issue: "SettingsLobeItem.mousePressEvent never executed (blocked by parent)"
      suggested_fix: "Events must propagate to this handler for single-click to work"
  missing:
    - "Click vs drag detection mechanism (position/time threshold)"
    - "Event propagation coordination between drag and click handlers"
    - "Only start dragging if click is NOT on interactive items"
  debug_session: ".planning/debug/widget-double-click.md"
- truth: "Widget source lobes (Mic/System) should respond to single click to toggle"
  status: failed
  reason: "User reported: Lobes do not respond to single click. They work with double click."
  severity: major
  test: 6
  root_cause: "Same as record button - parent widget event.accept() blocks all single-click events from reaching interactive items. ToggleLobeItem has correct mousePressEvent but never executes."
  artifacts:
    - path: "src/metamemory/widgets/main_widget.py:147-161"
      issue: "Parent widget consumes click events before items can handle them"
      suggested_fix: "Don't accept events on interactive items"
    - path: "src/metamemory/widgets/main_widget.py:481-487"
      issue: "ToggleLobeItem.mousePressEvent never executed"
      suggested_fix: "Events must propagate to this handler"
  missing:
    - "Click vs drag detection mechanism"
    - "Event propagation coordination"
  debug_session: ".planning/debug/widget-double-click.md"
- truth: "Crash recovery should only prompt when there are actual crash leftovers, not on every startup"
  status: failed
  reason: "User reported: Recovery works correctly, BUT prompts on every startup even when app closed properly and wasn't recording. False positive detection."
  severity: major
  test: 8
  root_cause: "finalize_stem() is called with default delete_part=False during normal recording finalization, leaving .pcm.part files in the directory after successful WAV creation. On subsequent startup, has_partial_recordings() detects these as crash leftovers, causing false positive recovery prompts."
  artifacts:
    - path: "src/metamemory/audio/session.py:326-329"
      issue: "finalize_stem() called without delete_part=True, so .pcm.part files persist after successful finalization"
      suggested_fix: "Add delete_part=True parameter to clean up .pcm.part files after successful WAV creation"
    - path: "src/metamemory/audio/storage/wav_finalize.py:79-113"
      issue: "finalize_stem() has delete_part=False default, preserving .pcm.part files after finalization"
      suggested_fix: "Change default to True, or explicitly pass True from session.stop()"
    - path: "src/metamemory/audio/storage/recovery.py:15-36"
      issue: "find_part_files() returns ALL .pcm.part files without distinguishing completed from incomplete recordings"
      suggested_fix: "No fix needed here - cleanup after finalization is the correct solution"
  missing:
    - "Cleanup of .pcm.part files after successful finalization"
  debug_session: ".planning/debug/crash-recovery-false-positive.md"
