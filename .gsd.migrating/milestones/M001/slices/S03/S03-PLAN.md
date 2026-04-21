# S03: Remove Enhancement Code

**Goal:** Remove all dual-mode enhancement code from the codebase — enhancement module, config models, UI controls, pipeline integration, and related tests.
**Demo:** Application runs without enhancement code; all existing tests pass; no orphaned imports or dead references.

## Must-Haves

- All enhancement-related code removed without breaking transcription pipeline
- Existing tests pass after removal
- No orphaned imports or dead enhancement references

## Tasks

- [ ] **T01: Remove enhancement.py and confidence filtering**
  - Delete `src/metamemory/transcription/enhancement.py` (5,188 lines)
  - Remove `should_enhance` and enhancement-related imports from `streaming_pipeline.py`
  - Remove enhancement queue/worker initialization and segment enqueueing from the pipeline
  - Remove enhancement-related imports from `accumulating_processor.py`
  - Verify transcription pipeline still works end-to-end without enhancement

- [ ] **T02: Remove EnhancementSettings from config models**
  - Remove `EnhancementSettings` dataclass from `src/metamemory/config/models.py`
  - Remove enhancement field from `AppSettings`
  - Remove enhancement-related config loading/saving in `config/manager.py`
  - Remove enhancement exports from `config/__init__.py`

- [ ] **T03: Remove enhancement UI from widgets**
  - Remove enhancement status bar, controls, and settings from `floating_panels.py`
  - Remove `enhancement_settings_changed` signal and handler from `main_widget.py`
  - Remove `Phrase.enhanced` field and bold formatting for enhanced segments
  - Remove enhancement-related signal connections

- [ ] **T04: Clean up tests and verify**
  - Remove or update any tests that reference enhancement functionality
  - Run full test suite to confirm no regressions
  - Grep for any remaining `enhance` references and clean up

## Files Likely Touched

- `src/metamemory/transcription/enhancement.py` (delete)
- `src/metamemory/transcription/streaming_pipeline.py`
- `src/metamemory/transcription/accumulating_processor.py`
- `src/metamemory/transcription/__init__.py`
- `src/metamemory/config/models.py`
- `src/metamemory/config/manager.py`
- `src/metamemory/config/__init__.py`
- `src/metamemory/widgets/floating_panels.py`
- `src/metamemory/widgets/main_widget.py`
- Various test files
