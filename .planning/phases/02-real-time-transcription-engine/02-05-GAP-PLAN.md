---
phase: 02-real-time-transcription-engine
plan: 05
type: gap_closure
gap_closure: true
wave: 3
depends_on: ["02-01", "02-04"]
files_modified:
  - requirements.txt
  - src/metamemory/transcription/engine.py
  - src/metamemory/transcription/__init__.py
  - src/metamemory/transcription/streaming_pipeline.py
  - tests/test_transcription_engine.py
  - tests/test_streaming_integration.py
autonomous: true

gap_reason: "PyTorch DLL initialization failure on Windows (WinError 1114). faster-whisper depends on torch which fails to load c10.dll. Need CPU-only, DLL-free alternative."

must_haves:
  truths:
    - "whisper.cpp replaces faster-whisper - no PyTorch/torch dependency"
    - "Same public API maintained - WhisperTranscriptionEngine class"
    - "Models download in .bin format (not .pt)"
    - "Confidence scores still extracted and normalized 0-100"
    - "All existing tests pass with new implementation"
  artifacts:
    - path: "src/metamemory/transcription/engine.py"
      provides: "WhisperTranscriptionEngine using whisper.cpp backend"
      exports: ["WhisperTranscriptionEngine", "TranscriptionSegment"]
---

<objective>
Replace faster-whisper with whisper.cpp to eliminate PyTorch DLL dependency causing launch failure on Windows.

Purpose: Fix WinError 1114 (DLL initialization) by switching to C++ implementation of Whisper that doesn't require torch/ctranslate2.
Output: Working transcription engine using whisper.cpp (via pywhispercpp or similar binding).
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-real-time-transcription-engine/RESEARCH.md

# Current broken state
@src/metamemory/transcription/engine.py
@requirements.txt

# What needs updating
@src/metamemory/transcription/streaming_pipeline.py
@src/metamemory/recording/controller.py
@src/metamemory/widgets/main_widget.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Research and install whisper.cpp Python bindings</name>
  <files>requirements.txt</files>
  <action>
    Research options for whisper.cpp in Python:
    
    Option A: pywhispercpp
    - pip install pywhispercpp
    - Python bindings for whisper.cpp
    - May need compilation on Windows
    
    Option B: whispercpp
    - pip install whispercpp
    - Alternative bindings
    
    Option C: Direct ctypes binding
    - Download whisper.dll + models
    - Write thin Python wrapper
    - Most control, most work
    
    RECOMMENDED: Try pywhispercpp first (easiest API).
    
    Steps:
    1. Remove from requirements.txt:
       - faster-whisper>=1.1.0
       - torch>=2.0.0
       - torchaudio>=2.0.0
       
    2. Add to requirements.txt:
       - pywhispercpp>=1.2.0
       - (or whispercpp if pywhispercpp fails)
       
    3. Install: pip install pywhispercpp
    
    4. Test import: python -c "from pywhispercpp import Whisper; print('OK')"
    
    If pywhispercpp fails to install/compile on Windows, fall back to:
    - Download pre-built whisper.dll from whisper.cpp releases
    - Write ctypes wrapper (about 100 lines)
  </action>
  <verify>python -c "from pywhispercpp import Whisper; print('whisper.cpp bindings OK')"</verify>
  <done>pywhispercpp or alternative installed and importable</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite WhisperTranscriptionEngine for whisper.cpp</name>
  <files>src/metamemory/transcription/engine.py</files>
  <action>
    Rewrite engine.py to use whisper.cpp instead of faster-whisper.
    
    MAINTAIN SAME PUBLIC API:
    - class WhisperTranscriptionEngine
    - __init__(model_size: str, device: str, compute_type: str)
    - load_model() -> None
    - is_model_loaded() -> bool  
    - transcribe_chunk(audio_np: np.ndarray) -> List[TranscriptionSegment]
    - normalize_confidence(avg_log_prob: float) -> int
    
    CHANGES NEEDED:
    1. Replace: from faster_whisper import WhisperModel
       With: from pywhispercpp import Whisper
       
    2. Model loading:
       - whisper.cpp models are .bin files (not .pt)
       - Download from: https://huggingface.co/ggerganov/whisper.cpp
       - Models: tiny.bin (~39M), base.bin (~74M), small.bin (~244M)
       - Store in: app data directory / models /
       
    3. Transcription API differences:
       - faster-whisper: segments = model.transcribe(audio, ...)
       - whisper.cpp: result = whisper.transcribe(audio_file_path)
       - Need to save audio chunk to temp file, transcribe, return results
       - OR use whisper.process_chunk() if available
       
    4. Confidence extraction:
       - whisper.cpp may not expose avg_log_prob directly
       - May need to parse output or use different metric
       - Research: whisper.cpp outputs token probabilities
       - Alternative: Use token confidence average from output
       
    5. Word timestamps:
       - whisper.cpp supports word-level timestamps
       - Enable via params: word_timestamps=True
       
    IMPLEMENTATION STRATEGY:
    ```python
    class WhisperTranscriptionEngine:
        def __init__(self, model_size="base", device="cpu", compute_type="int8"):
            self.model_size = model_size
            self.model = None
            self._model_dir = Path(app_data_dir) / "models"
            
        def load_model(self):
            model_path = self._model_dir / f"ggml-{self.model_size}.bin"
            if not model_path.exists():
                self._download_model(model_path)
            self.model = Whisper(str(model_path))
            
        def transcribe_chunk(self, audio_np: np.ndarray) -> List[TranscriptionSegment]:
            # Save to temp WAV file
            # Call whisper.transcribe(temp_path)
            # Parse results into TranscriptionSegment objects
            # Return list
    ```
    
    Handle API differences gracefully - maintain same return format.
  </action>
  <verify>python -c "from metamemory.transcription.engine import WhisperTranscriptionEngine; e = WhisperTranscriptionEngine('tiny'); e.load_model(); print(f'Model loaded: {e.is_model_loaded()}')"</verify>
  <done>Engine rewritten for whisper.cpp, maintains same API</done>
</task>

<task type="auto">
  <name>Task 3: Update streaming pipeline for new engine</name>
  <files>src/metamemory/transcription/streaming_pipeline.py</files>
  <action>
    Update streaming_pipeline.py if needed for whisper.cpp differences:
    
    Check:
    1. Does RealTimeTranscriptionProcessor still work with new engine?
    2. Are there any API changes in transcribe_chunk return format?
    3. Does threading model still work?
    
    LIKELY CHANGES:
    - Model loading may be faster/slower (whisper.cpp loads faster)
    - Inference may have different latency characteristics
    - May need to adjust chunk sizes for optimal performance
    
    ADAPTIVE CHUNKING:
    - whisper.cpp may prefer different audio formats
    - Test with 16kHz float32 (same as before)
    - If issues, try 16kHz int16
    
    Verify the integration still works end-to-end.
  </action>
  <verify>python -c "from metamemory.transcription.streaming_pipeline import RealTimeTranscriptionProcessor; from metamemory.config.models import TranscriptionSettings; c = TranscriptionSettings(); p = RealTimeTranscriptionProcessor(c); print('Pipeline OK')"</verify>
  <done>Streaming pipeline updated and compatible with whisper.cpp engine</done>
</task>

<task type="auto">
  <name>Task 4: Update or rewrite tests</name>
  <files>tests/test_transcription_engine.py, tests/test_streaming_integration.py</files>
  <action>
    Update tests for whisper.cpp:
    
    1. test_transcription_engine.py:
       - Update to use new engine API
       - Test model loading with .bin files
       - Test transcription with actual audio
       - Verify confidence extraction still works
       
    2. test_streaming_integration.py:
       - Verify end-to-end pipeline works
       - Test with FakeAudioModule
       - May need longer timeouts (model format conversion)
       
    NOTES:
    - First test run will download .bin models (~40MB for tiny)
    - whisper.cpp models download faster than torch models
    - Tests should pass with same assertions
    
    If pywhispercpp API is very different, may need to rewrite tests significantly.
  </action>
  <verify>cd C:\Users\david.keymel\Projects\metamemory && python -m pytest tests/test_transcription_engine.py tests/test_streaming_integration.py -v --timeout=180</verify>
  <done>All tests pass with whisper.cpp backend</done>
</task>

<task type="auto">
  <name>Task 5: Verify app launches without DLL errors</name>
  <files></files>
  <action>
    Final verification - app launches without torch DLL errors:
    
    1. Verify imports work:
       python -c "from metamemory.main import main; print('Import OK')"
       
    2. Try launching app (if possible in test environment):
       python -m metamemory.main
       
    3. Check no torch in dependency tree:
       pip list | grep -i torch (should return nothing)
       
    4. Check whisper.cpp loads:
       python -c "from metamemory.transcription.engine import WhisperTranscriptionEngine; print('whisper.cpp OK')"
       
    If any import errors, fix them before marking complete.
  </action>
  <verify>python -c "from metamemory.main import main; print('App imports successfully - no torch DLL errors')"</verify>
  <done>App launches without WinError 1114, all imports work</done>
</task>

</tasks>

<verification>
- faster-whisper and torch removed from requirements.txt
- pywhispercpp or whisper.cpp bindings installed
- WhisperTranscriptionEngine uses whisper.cpp backend
- Models download as .bin files (not .pt)
- Same public API maintained
- All tests pass
- App launches without DLL errors
</verification>

<success_criteria>
- No PyTorch/torch dependency in requirements.txt
- whisper.cpp backend functional
- WhisperTranscriptionEngine maintains same API
- Transcription works end-to-end
- All existing tests pass
- App launches without WinError 1114
</success_criteria>

<output>
After completion, create `.planning/phases/02-real-time-transcription-engine/02-05-SUMMARY.md`

Update STATE.md to reflect gap closure completion.
</output>
