# WIDGET Design Deviations

Intentional deviations from the original WIDGET requirements specification, documented for traceability.

---

## WIDGET-18: Transcript flows from widget

| Field | Detail |
|---|---|
| **Requirement ID** | WIDGET-18 |
| **Original Spec** | Transcript content flows directly out of the widget body, integrated as a continuous visual extension. |
| **Actual Implementation** | A separate `FloatingTranscriptPanel` QWidget docks adjacent to the main widget via `dock_to_widget()`. Both panels use a unified "glass pair" aesthetic: `WA_TranslucentBackground`, semi-transparent rgba backgrounds (230 alpha), subtle rgba borders (80 alpha), and matching idle opacity (0.87). The visual gap between widget and panel is small (10px) and both share the same translucent glass treatment so they read as a cohesive pair. |
| **Rationale** | Pragmatic architecture — integrating a scrolling text panel within the QGraphicsView scene that also hosts orbital animations would create complex layout conflicts and performance issues. A separate top-level QWidget provides clean separation of concerns, independent scrolling, and proper window management. The glass pair visual treatment ensures the panel and widget look like parts of the same UI rather than unrelated windows. |
| **Date** | 2025-04-27 |

---

## WIDGET-29: Enhanced segment bold styling

| Field | Detail |
|---|---|
| **Requirement ID** | WIDGET-29 |
| **Original Spec** | Enhanced bold styling for speaker-change segments in the transcript. |
| **Actual Implementation** | Dual-mode enhancement was removed during M001/S03 cleanup. Speaker segments use standard bold formatting via the transcript panel's `append_speaker_segment()` without a special enhanced mode. |
| **Rationale** | The dual-mode (normal/enhanced) styling added UI complexity without proportional user value. Standard bold speaker labels with colored indicators (WIDGET-21/22/23) provide sufficient visual differentiation. The enhancement was cut during initial cleanup to reduce surface area. |
| **Date** | 2025-04-27 |
