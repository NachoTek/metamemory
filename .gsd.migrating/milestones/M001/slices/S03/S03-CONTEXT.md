---
id: S03
milestone: M001
status: ready
---

# S03: Remove Enhancement Code — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

## Goal

Remove all dual-mode enhancement code from the codebase while preserving confidence color coding and post-recording transcription.

## Why this Slice

Dual-mode enhancement was removed from project scope (S04/S05 skipped). The enhancement code (5,188 lines in enhancement.py alone) is dead weight that clutters the codebase and confuses future development. Removing it now produces a clean baseline before any further feature work.

## Scope

### In Scope

- Delete `src/metamemory/transcription/enhancement.py` entirely (5,188 lines — EnhancementQueue, EnhancementWorkerPool, EnhancementProcessor, TranscriptUpdater, EnhancementConfig)
- Strip enhancement imports, initialization, and enqueueing from `streaming_pipeline.py` (107 references)
- Strip enhancement imports, initialization, and callback handling from `accumulating_processor.py` (108 references)
- Remove enhancement-specific functions from `confidence.py`: `should_enhance()`, `enhanced_confidence()`, `calculate_enhancement_eligibility()`
- Keep useful confidence functions: `normalize_confidence()`, `get_confidence_level()`, `get_confidence_color()`, `get_distortion_intensity()`, `ConfidenceLevel`, `ConfidenceLegendItem`
- Remove `EnhancementSettings` dataclass from `config/models.py` and `AppSettings.enhancement` field
- Remove enhancement config loading/saving from `config/manager.py` and `config/__init__.py`
- Remove enhancement UI from `floating_panels.py` (62 references) and `main_widget.py` (35 references)
- Remove enhancement-related signal connections and `Phrase.enhanced` field
- Remove `update_enhancement_settings()` and `get_enhancement_status()` from `controller.py`
- Remove enhancement references from `post_processor.py` (22 references) — keep PostProcessingQueue since it handles stronger-model post-recording transcription (not dual-mode enhancement)
- Remove enhancement test references from `tests/test_config.py` (6 references)
- Remove `enhanced` flag from `Word`/`Segment` in `transcript_store.py`
- Clean up enhancement references in `engine.py` (get_enhancement_model classmethod)
- Remove enhancement metadata from `fake_module.py`
- Grep for any remaining `enhance` references and clean up
- Full test suite passes after removal

### Out of Scope

- Adding new features
- Refactoring the remaining transcription pipeline architecture
- Changing the confidence color scheme or thresholds
- Removing PostProcessingQueue (it handles post-recording transcription with a stronger model — separate from dual-mode enhancement)

## Constraints

- Must not break the existing transcription pipeline
- All tests must pass after removal
- No orphaned imports or dead references
- Confidence color coding must continue working unchanged

## Integration Points

### Consumes

- S02's transcription modules (engine.py, accumulating_processor.py, streaming_pipeline.py, confidence.py) — need surgical removal of enhancement code
- S02's config system (models.py, manager.py) — need EnhancementSettings removal
- S02's widget code (floating_panels.py, main_widget.py) — need UI cleanup

### Produces

- Clean codebase with no enhancement code
- Tests passing without enhancement references
- Confidence coloring still functional
- PostProcessingQueue still operational for post-recording transcription

## Open Questions

- None — scope is clear from user confirmation
