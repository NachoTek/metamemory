# Phase 2: Real-Time Transcription Engine - Research

**Researched:** 2026-02-01
**Domain:** Whisper ASR real-time streaming with < 2s latency
**Confidence:** HIGH (multiple authoritative sources verified)

## Summary

This research addresses the technical questions for implementing real-time Whisper transcription with sub-2-second latency. The key findings are:

**Chunking Strategy:** Voice Activity Detection (VAD) with fixed minimum chunk sizes provides the best balance of latency and accuracy. Fixed windows alone split words; pure VAD can have unpredictable latency. The hybrid approach (VAD with min-chunk-size) is the state-of-the-art used by whisper_streaming.

**Optimal Chunk Size:** 1-2 seconds (1000-2000ms) is the sweet spot. Smaller chunks (< 1s) hurt accuracy significantly; larger chunks (> 3s) exceed the < 2s latency goal. With VAD, min-chunk-size of 1.0s is recommended.

**Chunk Overlap:** Not recommended for streaming. Instead, use buffer trimming with "local agreement policy" - commit text only after N consecutive iterations agree. This prevents duplication without the complexity of overlap management.

**Confidence Extraction:** `avg_log_prob` from segments is the most reliable metric. Token-level probabilities can be averaged for word-level confidence. Values range from ~-1.0 (high confidence) to ~-3.0 (low confidence), which can be normalized to 0-100%.

**Hardware Requirements:** RAM is the primary constraint. Model sizes: Tiny (39M params, ~400MB RAM), Base (74M, ~1GB), Small (244M, ~2GB). CPU inference on modern hardware can achieve real-time factors (RTF) of 0.3-0.8x with faster-whisper using int8 quantization.

**Primary recommendation:** Use faster-whisper with VAD-enabled streaming, 1.0s min-chunk-size, int8 quantization for CPU, and buffer trimming based on local agreement. Target < 2s latency with base model on modern CPUs.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| faster-whisper | 1.1.0+ | Primary inference engine | 4x faster than openai-whisper, same accuracy, CTranslate2 optimized |
| whisper.cpp | 1.7.0+ | Alternative for resource-constrained | Best CPU performance, ultra-low memory, C++ implementation |
| silero-vad | built-in | Voice activity detection | Faster-whisper includes Silero VAD, proven in production |

### Supporting

| Library | Purpose | When to Use |
|---------|---------|-------------|
| whisper_streaming | Reference implementation | Study for streaming architecture patterns |
| numpy | Audio buffer manipulation | Essential for audio preprocessing |
| torch/torchaudio | VAC (Voice Activity Controller) | Required for whisper_streaming VAC feature |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| faster-whisper | openai-whisper | Simpler but 4x slower, higher memory |
| faster-whisper | whisper.cpp | whisper.cpp faster on CPU but harder Python integration |
| VAD chunking | Fixed windows | Fixed windows simpler but split words, hurt accuracy |
| Local agreement | Simple overlap | Overlap causes duplication issues, harder to manage |

**Installation:**
```bash
# Recommended stack
pip install faster-whisper numpy

# For VAC (Voice Activity Controller)
pip install torch torchaudio

# Optional: whisper.cpp Python bindings
pip install pywhispercpp
```

## Architecture Patterns

### Recommended Project Structure

```
transcription/
├── audio_buffer.py       # Ring buffer for audio chunks
├── vad_processor.py      # Voice activity detection wrapper
├── inference_engine.py   # Whisper model wrapper
├── streaming_processor.py # Main orchestration logic
├── confidence_scorer.py  # Confidence extraction/normalization
└── config.py             # Settings and hardware detection
```

### Pattern 1: VAD with Minimum Chunk Size (RECOMMENDED)

**What:** Use Silero VAD to detect speech, but enforce a minimum chunk size (e.g., 1.0s) before processing. Accumulate audio until either (a) VAD detects speech end OR (b) min-chunk-size is reached.

**When to use:** General real-time transcription where latency < 2s is acceptable.

**Example (pseudocode):**
```python
# Source: faster-whisper VAD integration pattern
# https://github.com/SYSTRAN/faster-whisper

class VADChunkingProcessor:
    def __init__(self, min_chunk_size_sec=1.0, sample_rate=16000):
        self.min_chunk_size = int(min_chunk_size_sec * sample_rate)
        self.buffer = []
        
    def process_audio(self, audio_chunk, vad_result):
        self.buffer.extend(audio_chunk)
        
        # Process if we have minimum chunk OR speech ended
        if len(self.buffer) >= self.min_chunk_size or vad_result.is_speech_end:
            audio_to_process = self.buffer[:self.min_chunk_size]
            self.buffer = self.buffer[self.min_chunk_size:]
            return audio_to_process
        return None
```

### Pattern 2: Local Agreement Buffer Trimming (Anti-Duplication)

**What:** Don't emit transcribed text immediately. Keep a buffer of recent transcriptions and only "commit" text when N consecutive iterations produce the same prefix.

**When to use:** Streaming display to prevent text "flickering" and duplication.

**Example (based on whisper_streaming):**
```python
# Source: whisper_streaming whisper_online.py
# https://github.com/ufal/whisper_streaming

class LocalAgreementBuffer:
    def __init__(self, agreement_threshold=2):
        self.buffer = []
        self.committed_text = ""
        self.agreement_count = 0
        self.agreement_threshold = agreement_threshold
        
    def process_iteration(self, new_transcription):
        # Find common prefix with previous transcription
        common_prefix = self._common_prefix(self.buffer, new_transcription)
        
        if common_prefix == self.buffer:
            self.agreement_count += 1
        else:
            self.agreement_count = 0
            self.buffer = common_prefix
            
        # Commit if agreement threshold reached
        if self.agreement_count >= self.agreement_threshold:
            to_commit = self.buffer[len(self.committed_text):]
            self.committed_text = self.buffer
            return to_commit
        return ""
        
    def _common_prefix(self, a, b):
        min_len = min(len(a), len(b))
        for i in range(min_len):
            if a[i] != b[i]:
                return a[:i]
        return a[:min_len]
```

### Pattern 3: Sliding Window with Overlap (NOT RECOMMENDED)

**What:** Process overlapping chunks (e.g., 3s chunks with 1s overlap). Requires deduplication logic.

**Why it's problematic:** Whisper's attention mechanism means overlapping chunks get different context, leading to inconsistent transcriptions. Deduplication is complex and error-prone.

**Verdict:** Use buffer trimming instead (Pattern 2).

### Anti-Patterns to Avoid

- **Simple fixed windows without VAD:** Splits words at boundaries, hurts accuracy significantly (verified in whisper_streaming paper).
- **Processing every small chunk (< 500ms):** Whisper needs context; tiny chunks produce garbage.
- **Immediate emission without agreement:** Causes text flickering and user confusion.
- **Chunk overlap without deduplication:** Results in repeated text.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VAD implementation | Custom energy-based VAD | Silero VAD (built into faster-whisper) | Silero is ML-based, handles noise/music, proven in production |
| Streaming orchestration | Simple loop with sleep | whisper_streaming architecture | They've solved edge cases (timestamps, agreement, buffer overflow) |
| Audio decoding | Manual FFmpeg wrapping | PyAV (faster-whisper uses this) | Handles formats, resampling, edge cases |
| Confidence normalization | Simple sigmoid on log_prob | See Pattern below | Whisper's log probabilities have specific ranges |

**Key insight:** The "simple" approach of processing fixed chunks in a loop fails on real speech patterns. Use the VAD + local agreement pattern from whisper_streaming.

## Common Pitfalls

### Pitfall 1: Word Splitting at Chunk Boundaries

**What goes wrong:** Fixed 1s chunks cut words in half. Whisper sees "conver" in one chunk and "sation" in another, producing nonsense.

**Why it happens:** Speech has variable rate; words don't align to fixed time windows.

**How to avoid:** Use VAD-based segmentation. Silero VAD detects speech boundaries naturally.

**Warning signs:** Transcriptions showing partial words like "conver-" or "-sation".

### Pitfall 2: Text Duplication in Streaming Display

**What goes wrong:** Same text appears multiple times with slight variations.

**Why it happens:** Processing overlapping chunks or not properly managing the committed/uncommitted text boundary.

**How to avoid:** Implement local agreement (Pattern 2). Track "committed" vs "volatile" text separately.

### Pitfall 3: Inaccurate Timestamps

**What goes wrong:** Word timestamps drift or are completely wrong in streaming mode.

**Why it happens:** Whisper's attention mechanism maps audio positions to text positions. Small chunks lose absolute time reference.

**How to avoid:** Use word-level timestamps from faster-whisper (`word_timestamps=True`). Track cumulative buffer offset.

### Pitfall 4: Memory Leaks in Audio Buffer

**What goes wrong:** Application memory grows unbounded during long sessions.

**Why it happens:** Accumulating all audio in a growing list without trimming.

**How to avoid:** Use a ring buffer or list with explicit trimming. Trim committed audio after processing (keep only uncommitted + context window).

### Pitfall 5: Model Loading Blocking UI

**What goes wrong:** UI freezes for several seconds when starting transcription.

**Why it happens:** Loading Whisper model is CPU-intensive and synchronous.

**How to avoid:** Load model in background thread before user starts transcription. Show loading indicator during initialization.

## Code Examples

### Recommended: faster-whisper with VAD

```python
# Source: faster-whisper documentation + best practices
# https://github.com/SYSTRAN/faster-whisper

from faster_whisper import WhisperModel
import numpy as np

class WhisperTranscriptionEngine:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        # Load model (do this once, not per-transcription)
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        
    def transcribe_chunk(self, audio_np: np.ndarray) -> tuple:
        """
        Transcribe audio chunk with confidence scores.
        
        Returns: (text, confidence_0_to_100, word_timestamps)
        """
        segments, info = self.model.transcribe(
            audio_np,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,  # Enable Silero VAD
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200
            )
        )
        
        results = []
        for segment in segments:
            # Extract confidence from avg_log_prob
            # Whisper log_probs: -1.0 = high confidence, -3.0 = low
            confidence = self._normalize_confidence(segment.avg_log_prob)
            
            words = []
            if segment.words:
                for word in segment.words:
                    words.append({
                        'text': word.word,
                        'start': word.start,
                        'end': word.end,
                        'confidence': confidence  # Per-segment confidence
                    })
            
            results.append({
                'text': segment.text,
                'confidence': confidence,
                'words': words,
                'start': segment.start,
                'end': segment.end
            })
            
        return results
    
    def _normalize_confidence(self, avg_log_prob: float) -> int:
        """
        Convert Whisper's avg_log_prob to 0-100 scale.
        
        Whisper log probabilities:
        - -1.0 to -1.5: High confidence
        - -2.0: Medium confidence  
        - -3.0 or lower: Low confidence
        """
        # Clamp and normalize
        if avg_log_prob > -1.0:
            return 95
        elif avg_log_prob < -3.0:
            return 30
        else:
            # Linear interpolation from [-3.0, -1.0] to [30, 95]
            normalized = (avg_log_prob - (-3.0)) / (-1.0 - (-3.0))
            return int(30 + normalized * 65)
```

### Audio Buffer with Ring Buffer Pattern

```python
# Ring buffer for efficient audio management

class AudioRingBuffer:
    """Fixed-size ring buffer for audio chunks with automatic trimming."""
    
    def __init__(self, max_seconds: int = 30, sample_rate: int = 16000):
        self.max_samples = max_seconds * sample_rate
        self.buffer = np.array([], dtype=np.float32)
        self.total_samples_seen = 0
        
    def append(self, chunk: np.ndarray):
        """Add audio chunk, trimming old audio if needed."""
        self.buffer = np.concatenate([self.buffer, chunk])
        self.total_samples_seen += len(chunk)
        
        # Trim if exceeds max size (keep most recent)
        if len(self.buffer) > self.max_samples:
            self.buffer = self.buffer[-self.max_samples:]
            
    def get_recent(self, seconds: float) -> np.ndarray:
        """Get most recent N seconds of audio."""
        samples = int(seconds * 16000)
        return self.buffer[-samples:] if len(self.buffer) >= samples else self.buffer
        
    def trim_committed(self, committed_samples: int):
        """Remove audio that has been committed to transcript."""
        if committed_samples > 0:
            self.buffer = self.buffer[committed_samples:]
```

### Real-Time Streaming Loop

```python
import threading
import queue
import time

class RealTimeTranscriptionProcessor:
    def __init__(self, engine: WhisperTranscriptionEngine, 
                 min_chunk_sec: float = 1.0):
        self.engine = engine
        self.min_chunk_samples = int(min_chunk_sec * 16000)
        self.audio_buffer = AudioRingBuffer()
        self.result_queue = queue.Queue()
        self.is_running = False
        self.processing_thread = None
        
    def start(self):
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.start()
        
    def stop(self):
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
            
    def feed_audio(self, chunk: np.ndarray):
        """Call this from audio capture callback."""
        self.audio_buffer.append(chunk)
        
    def _processing_loop(self):
        """Background thread for inference."""
        while self.is_running:
            # Check if we have enough audio
            if len(self.audio_buffer.buffer) >= self.min_chunk_samples:
                # Get chunk for processing
                chunk = self.audio_buffer.get_recent(
                    len(self.audio_buffer.buffer) / 16000
                )
                
                # Transcribe (this blocks, hence the thread)
                results = self.engine.transcribe_chunk(chunk)
                
                # Queue results for main thread
                for r in results:
                    self.result_queue.put(r)
                    
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
            else:
                time.sleep(0.05)  # Wait for more audio
                
    def get_results(self) -> list:
        """Get pending results (call from main thread)."""
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get())
        return results
```

## Hardware Requirements

### Model Specifications

| Model | Parameters | Model Size | RAM (fp32) | RAM (int8) | CPU RTF* | Notes |
|-------|------------|------------|------------|------------|----------|-------|
| tiny | 39M | ~75 MB | ~400 MB | ~200 MB | 0.1-0.2x | Fastest, lowest accuracy |
| base | 74M | ~150 MB | ~1 GB | ~500 MB | 0.2-0.4x | Good balance |
| small | 244M | ~460 MB | ~2 GB | ~1.5 GB | 0.5-0.8x | Recommended for < 2s latency |
| medium | 769M | ~1.4 GB | ~5 GB | ~3 GB | 1.0-2.0x | May exceed latency target on CPU |
| large | 1550M | ~3 GB | ~10 GB | ~6 GB | 2.0x+ | Not recommended for CPU real-time |

*RTF (Real-Time Factor) = processing time / audio duration. < 1.0 means faster than real-time.
**CPU RTF measured on modern Intel i7/i9 or AMD Ryzen 7/9 with 8+ threads.

### Hardware Recommendations by Use Case

| Hardware | Recommended Model | Expected Latency | Notes |
|----------|-------------------|------------------|-------|
| Low-end (4GB RAM, old CPU) | tiny | 1-2s | May struggle with base model |
| Mid-range (8GB RAM, modern i5/Ryzen 5) | base | 0.5-1.5s | Good balance |
| High-end (16GB+ RAM, i7/Ryzen 7+) | small | 0.5-1.0s | Best accuracy for < 2s target |
| Apple Silicon (M1/M2/M3) | small | 0.3-0.8s | Use whisper.cpp or mlx-whisper |

### Auto-Detection Algorithm

```python
import psutil

def recommend_model() -> str:
    """Auto-recommend Whisper model based on hardware."""
    ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count(logical=True)
    
    if ram_gb < 6 or cpu_count < 4:
        return "tiny"
    elif ram_gb < 12 or cpu_count < 8:
        return "base"
    else:
        return "small"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed window chunking | VAD-based segmentation | 2023 | Better accuracy, natural boundaries |
| Simple overlap | Local agreement policy | 2023 | No duplication, stable output |
| openai-whisper | faster-whisper | 2023 | 4x speedup, lower memory |
| Greedy decoding (beam=1) | Beam search (beam=5) | 2024 | Better accuracy, minimal latency cost |
| FP32 inference | INT8 quantization | 2024 | 50% memory reduction, 20% speedup |

**Deprecated/outdated:**
- **Simple energy-based VAD:** Silero VAD is now standard, far more accurate
- **Processing every 0.5s:** Proven to hurt accuracy; 1s minimum is standard
- **CPU-only for small models:** Modern quantization makes small model viable on most hardware

## Open Questions

1. **Whisper Turbo Model Integration**
   - What we know: OpenAI released "turbo" model in 2024, optimized for speed
   - What's unclear: Real-world RTF on CPU, accuracy tradeoffs vs small model
   - Recommendation: Evaluate turbo model alongside small for Phase 2; may replace small as default

2. **Dynamic Chunk Size Adjustment**
   - What we know: Speech rate varies; 1s may be too short for slow speakers
   - What's unclear: Algorithm for dynamic adjustment without hurting latency
   - Recommendation: Start with fixed 1s, add dynamic adjustment as Phase 2 enhancement

3. **Multi-language Confidence Calibration**
   - What we know: Log probability ranges vary by language
   - What's unclear: Per-language normalization curves
   - Recommendation: Use simple global normalization for Phase 2, per-language tuning as future work

## Sources

### Primary (HIGH confidence)
- **faster-whisper GitHub** (SYSTRAN) - https://github.com/SYSTRAN/faster-whisper
  - Benchmarks verified: 4x speedup vs openai-whisper
  - Memory usage: Verified with int8 quantization numbers
  - VAD integration: Silero VAD built-in

- **whisper_streaming GitHub** (ufal) - https://github.com/ufal/whisper_streaming
  - Local agreement policy implementation
  - Chunking strategy: VAD with min-chunk-size
  - Latency benchmarks: 3.3s on unsegmented speech (with large model)

- **Whisper Streaming Research Paper** (Macháček et al., 2023) - https://aclanthology.org/2023.ijcnlp-demo.3/
  - Academic validation of streaming approach
  - Comparison of chunking strategies
  - Buffer trimming evaluation

### Secondary (MEDIUM confidence)
- **Whisper.cpp benchmarks** - Verified CPU RTF numbers on Intel i7
- **Hugging Face model cards** - Memory requirements for each model size
- **Silero VAD documentation** - VAD parameters and behavior

### Tertiary (LOW confidence)
- **Community implementations** (WhisperLive, RealtimeSTT) - Architecture patterns
- **Picovoice benchmarks** - Competitive comparison data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with faster-whisper official benchmarks
- Architecture patterns: HIGH - Based on whisper_streaming paper + implementation
- Pitfalls: MEDIUM-HIGH - Based on GitHub issues + research papers
- Hardware specs: HIGH - Verified with official model cards + benchmarks

**Research date:** 2026-02-01
**Valid until:** 2026-05-01 (faster-moving domain, check for whisper turbo updates)

---

*Research conducted for Phase 2: Real-Time Transcription Engine*
*Questions answered: Audio chunking, chunk size, overlap strategy, confidence extraction, hardware requirements*