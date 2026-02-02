# Phase 2: Real-Time Transcription Engine - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate Whisper models for real-time transcription with < 2s latency. This phase builds the core transcription pipeline - how audio becomes text in real-time. Includes model selection, audio chunking, inference pipeline, confidence scoring, and settings persistence.

**Scope:**
- Whisper model integration (tiny/base/small)
- Real-time audio chunking and buffering
- Transcription inference pipeline  
- Confidence score extraction and visualization
- Hardware detection and model recommendations
- Settings persistence across restarts

**Out of scope:**
- Speaker identification (Phase 4)
- Dual-mode enhancement (Phase 3)
- UI widget design (Phase 5)
- System monitoring (Phase 6)

</domain>

<decisions>
## Implementation Decisions

### Audio Chunking Strategy
- **Approach:** To be researched - evaluate fixed windows vs VAD vs silence-based for live transcription
- **Chunk size:** To be researched - balance between latency (< 2s goal) and Whisper's context needs
- **Overlap strategy:** To be researched - determine if/when chunks should overlap
- **Transcript placement:** Use Whisper's timestamp mode to place words at actual time positions, avoiding duplication issues

### Confidence Scoring & Display
- **Extraction method:** To be researched - evaluate Whisper's log_prob vs token probabilities
- **Display:** Show exact confidence percentage inline with transcript text
- **Visual effect:** Apply wavy/blur distortion to low-confidence text (more distortion = lower confidence)
- **Effect thresholds:** 
  - 85%+ confidence: no effect
  - Below 85%: effect intensity scales linearly toward 0%
  - Maximum effect at 0% must be capped to maintain text readability
- **Phase 3 integration:** Confidence feeds into enhancement decisions with user-adjustable threshold (default ~70%)

### Hardware Recommendations
- **Approach:** Auto-recommend model size on first run based on hardware detection
- **User override:** User can override recommendation, but defaults to auto-detected optimal
- **Detection criteria:** To be researched - determine which hardware specs (RAM, CPU, GPU) matter most
- **GPU:** CPU-only inference for simplicity (no GPU support in Phase 2)
- **Re-detection:** Offer "Re-detect hardware" option in settings for when users upgrade
- **Model download:** Prompt user to confirm download after recommendation (transparent, not automatic)
- **Performance alerts:** If selected model performs poorly (high latency), alert user with suggestion to try smaller model

### Settings Persistence
- **Scope:** Smart defaults with overrides - only persist settings user has explicitly changed
- **Storage location:** JSON config file in application directory
- **Format:** JSON (human-readable, standard, easy to parse)
- **Versioning:** Versioned configs - store config version, migrate on version mismatch
- **Settings UI:** Settings lobe expands to display settings interface (similar to transcript panel)
- **Organization:** Settings grouped into tabs to maximize content in compact space

### Transcript Formatting
- **Display mode:** Word-by-word streaming - each word appears as transcribed
- **Punctuation:** To be researched - how to handle mid-sentence punctuation with word-by-word display

### Claude's Discretion
- Buffer sizing and memory management for audio chunks
- Specific Whisper library/wrapper choice (openai-whisper, faster-whisper, whisper.cpp, etc.)
- Error handling and recovery strategies
- Threading model for inference (separate thread, async, etc.)
- Audio preprocessing before Whisper (normalization, silence trimming)

</decisions>

<specifics>
## Specific Ideas

- Use Whisper's timestamp mode to avoid text duplication when chunks overlap or when using word-by-word display
- Confidence visualization: wavy/blur distortion effect that intensifies as confidence drops (below 85%)
- Settings lobe expands similarly to how transcript panel will work (Phase 5) - tabs for organization

</specifics>

<deferred>
## Deferred Ideas

- **GPU acceleration:** Explicitly deferred - CPU-only for Phase 2 simplicity, can add GPU support later if needed
- **Advanced VAD:** Voice Activity Detection with machine learning - could be added later for smarter chunking
- **Custom language models:** Fine-tuned Whisper models for specific domains (medical, legal) - future enhancement
- **Offline mode improvements:** Pre-bundling multiple models - can improve first-run experience in future

</deferred>

---

*Phase: 02-real-time-transcription-engine*
*Context gathered: 2026-02-01*
