# Phase 03: Dual-Mode Enhancement Architecture - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Background large model enhancement with selective processing and live UI updates. Dual-mode runs large Whisper (medium/large) in parallel with real-time transcription to enhance low-confidence segments. This is the core innovation that differentiates the product.

</domain>

<decisions>
## Implementation Decisions

### Enhancement Triggering Criteria
- **Threshold:** Fixed at <70% confidence (user-configurable in settings)
- **Granularity:** Per-word (each low-confidence word is a candidate)
- **Batching:** If 3+ consecutive words are low-confidence, enhance as a phrase for better context
- **Trigger timing:** 5-second batch window (collect candidates, then process)
- **Confidence source:** Use existing per-word scores from real-time transcription
- **Minimum length:** Enhance any length, even single words
- **Duplicates:** One enhancement per segment maximum (mark as 'enhanced', never re-queue)
- **Cooldown:** Adaptive based on system load
- **Failures:** Keep original transcription if enhancement fails
- **Always-on:** Enhancement runs continuously in background during recording (not disableable mid-recording)
- **Scope:** Only fix low-confidence (no "polish" mode for high-confidence segments)
- **Special handling:** Treat proper nouns same as other words (no special pattern matching)

### Worker Pool Management
- **Worker count:** Fixed 2 workers (simple, predictable)
- **Resource constraints:** Slow down processing when system busy (don't pause entirely)
- **Job assignment:** Round-robin per segment
- **Model size:** Claude's discretion based on performance testing
- **Post-recording:** Stop all workers when recording ends, use final enhanced output for transcript
- **Timeout:** Smart adaptive timeout based on first-startup benchmark of known audio segment
- **Persistence:** Keep workers warm for 5 minutes between recordings
- **Visibility:** 
  - Normal mode: Workers completely invisible to users
  - Debug mode: Detailed diagnostics panel showing worker count, queue depth, items/minute, etc.

### UI Update Behavior
- **Visual distinction:** Bold text only for enhanced segments
- **Transition:** Smooth 300ms fade (original fades out, enhanced fades in)
- **Scrolling:** Update in background (no auto-scroll or notification if user scrolled away)
- **Editing:** No live editing of transcript text — editing reserved for separate "review" workflow

### Enhancement Queue Visualization
- **Normal mode:** No indication at all that enhancement is happening
- **Debug mode:** Queue depth (count) visible in debug panel

### Claude's Discretion
- **Model size selection:** Choose between medium vs large based on performance testing
- **Exact timeout calculation:** Determine optimal adaptive timeout algorithm
- **Debug panel details:** Decide what specific worker diagnostics to show

</decisions>

<specifics>
## Specific Ideas

- Enhancement is supposed to try to run alongside standard recording mode
- Debug mode toggle in settings will show panel with worker details (count, queue items, processing rate, etc.)
- No transcription text should be editable live — this feature reserved for if user chooses to "review" recordings before sending them to next workflow step

</specifics>

<deferred>
## Deferred Ideas

- No deferred ideas — discussion stayed within phase scope

</deferred>

---

*Phase: 03-dualmodeenhancementarchitecture*
*Context gathered: 2026-02-10*